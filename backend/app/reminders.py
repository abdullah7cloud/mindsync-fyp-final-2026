"""
Deadline reminders, version 2.

What a student can set (Settings): which lead times (1 h ... 7 days before a deadline), an optional same-day reminder at a chosen hour,
an optional overdue reminder, and their time zone. With nothing set it behaves exactly like version 1: one e-mail 48 hours before a
deadline, once per task.

How duplicates are prevented: every reminder has a key (task + kind + the deadline it was for) that is written to `reminder_log`
under a unique constraint. A changed deadline gives a new key, so it re-arms itself ("rescheduling"). Several lead times that are all
already due (a task created two hours before its deadline) send ONE e-mail for the closest one; the others are logged as skipped.

Honest delivery states: `sent` means the mail server accepted the message; it is NOT proof it reached an inbox. `outbox` means no
mail server is set up and the message was only saved as a file. `failed` keeps a short error code (never the server's text, never a
password) and is retried up to 5 times, 15 minutes apart, then left alone.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.assist.models import ReminderLog, UserSettings
from app.assist.settings_schema import settings_from
from app.models import Task, TaskStatus, User

log = logging.getLogger("mindsync.reminders")
MAX_ATTEMPTS = 5
RETRY_AFTER = timedelta(minutes=15)
OVERDUE_WINDOW = timedelta(hours=72)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass
class Due:
    task: Task
    kind: str                 # lead | same_day | overdue
    key: str
    label: str
    superseded: tuple = ()    # keys of larger lead times that are covered by this one


def decide(user: User, st, tasks: list, now: datetime) -> list:
    """Pure decision: which reminders are due for this student right now (no database, no sending)."""
    if not user.email_alerts or not st.remind_enabled:
        return []
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(st.timezone)
    local = now.astimezone(tz)
    out = []
    for t in tasks:
        if t.status != TaskStatus.pending:
            continue
        dl = _aware(t.deadline)
        dl_key = dl.astimezone(timezone.utc).strftime("%Y%m%dT%H%M")
        sent_at = _aware(t.reminder_sent_at) if t.reminder_sent_at else None
        if dl > now:
            due_leads = []
            for L in sorted(st.remind_lead_hours, reverse=True):
                trig = dl - timedelta(hours=L)
                if trig <= now and not (sent_at and trig <= sent_at):
                    due_leads.append(L)
            if due_leads:
                closest = min(due_leads)
                out.append(Due(t, "lead", f"lead{closest}:{t.id}:{dl_key}", f"{closest}h",
                               tuple(f"lead{L}:{t.id}:{dl_key}" for L in due_leads if L != closest)))
            if st.same_day_reminder and dl.astimezone(tz).date() == local.date() and local.hour >= st.same_day_hour:
                out.append(Due(t, "same_day", f"same_day:{t.id}:{local.date().isoformat()}:{dl_key}", "today"))
        elif st.overdue_reminder and now - dl <= OVERDUE_WINDOW:
            out.append(Due(t, "overdue", f"overdue:{t.id}:{dl_key}", "overdue"))
    return out


async def _existing(db: AsyncSession, user_id, keys: list) -> dict:
    if not keys:
        return {}
    rows = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == user_id, ReminderLog.dedupe_key.in_(keys)))).all()
    return {r.dedupe_key: r for r in rows}


async def run_cycle(db: AsyncSession, now: Optional[datetime] = None, only_user: Optional[uuid.UUID] = None, sender: Optional[Callable] = None) -> dict:
    from app import notifier
    sender = sender or notifier.deliver
    now = now or datetime.now(timezone.utc)
    q = select(User).where(User.email_alerts.is_(True))
    if only_user is not None:
        q = q.where(User.id == only_user)
    users = (await db.scalars(q)).all()
    emails = alerted = failures = skipped = 0
    mode = notifier.delivery_mode()
    for user in users:
        row = await db.get(UserSettings, user.id)
        st = settings_from(row.data if row else None)
        tasks = (await db.scalars(select(Task).where(Task.owner_id == user.id, Task.status == TaskStatus.pending))).all()
        due = decide(user, st, tasks, now)
        if not due:
            continue
        logs = await _existing(db, user.id, [d.key for d in due] + [k for d in due for k in d.superseded])
        todo = []
        for d in due:
            prev = logs.get(d.key)
            if prev is not None:
                if prev.status in ("sent", "outbox", "skipped"):
                    continue
                if prev.status == "failed" and (prev.attempts >= MAX_ATTEMPTS or now - _aware(prev.created_at) < RETRY_AFTER):
                    continue
            todo.append(d)
        for d in due:                                    # larger lead times covered by a closer one are recorded, never sent
            for k in d.superseded:
                if k not in logs:
                    db.add(ReminderLog(user_id=user.id, task_id=d.task.id, kind="lead", dedupe_key=k, status="skipped", detail="covered by a closer reminder", created_at=now))
                    skipped += 1
        if not todo:
            await _commit_quietly(db)
            continue
        groups = {"lead": [], "same_day": [], "overdue": []}
        for d in todo:
            groups[d.kind].append(d.task)
        msg = notifier.build_digest_email(user, groups, now, st.timezone)
        try:
            mode = await sender(msg)
            status_, detail = ("sent" if mode == "smtp" else "outbox"), ("accepted by the mail server" if mode == "smtp" else "saved as a file; no mail server is set up")
            err = False
        except Exception as exc:  # network/SMTP problems must never crash the job
            code, _hint = notifier.classify_mail_error(exc)
            log.warning("Could not send reminder to user %s: %s (%s)", user.id, code, type(exc).__name__)
            status_, detail, err = "failed", f"error: {code}", True
            failures += 1
        for d in todo:
            prev = logs.get(d.key)
            if prev is not None:
                prev.attempts += 1
                prev.status, prev.detail, prev.created_at = status_, detail, now
            else:
                db.add(ReminderLog(user_id=user.id, task_id=d.task.id, kind=d.kind, dedupe_key=d.key, status=status_, detail=detail, created_at=now))
            if not err and d.kind == "lead":
                d.task.reminder_sent_at = now
        if not err:
            emails += 1
            alerted += len(todo)
        await _commit_quietly(db)
    return {"emails": emails, "tasks": alerted, "failures": failures, "skipped": skipped, "mode": mode}


async def _commit_quietly(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError:        # two cycles raced for the same key: the unique constraint did its job, nothing is sent twice
        await db.rollback()
