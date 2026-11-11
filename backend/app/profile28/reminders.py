"""
Task e-mail reminders (Settings page).

Rule: a reminder is sent once for a task when X% of the time between the moment the task was made and its deadline is still left (X is 30 or 35).
Example: a task made 10 days before its deadline gets its e-mail when 3 days remain (30%).
The deadline is the END of the task's due date (23:59) in the student's own time zone. Completed and deleted tasks never get an e-mail.

Duplicates are impossible: before anything is sent, a row (task + due date) is inserted under a UNIQUE key. If two schedulers race, one insert fails and
that scheduler sends nothing. A change of the due date is a new key, so the task is armed again. A failed send is retried up to 5 times, 15 minutes apart.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import notifier
from app.models import User
from app.simple.models import STask

from .mail import build_task_reminder
from .models import Preferences, TaskReminder

log = logging.getLogger("mindsync.profile28")
PERCENTS = (30, 35)
MAX_ATTEMPTS = 5
RETRY_AFTER = timedelta(minutes=15)
STALE_CLAIM = timedelta(minutes=30)
MAX_PER_EMAIL = 15


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def safe_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def deadline_of(due: date, tz_name: str) -> datetime:
    """End of the due date in the student's time zone, as UTC."""
    return datetime.combine(due, time(23, 59), tzinfo=safe_zone(tz_name)).astimezone(timezone.utc)


def trigger_of(created_at: datetime, deadline: datetime, percent: int) -> Optional[datetime]:
    """The moment when `percent` % of the time (task made -> deadline) is left. None if the task has no time span."""
    start = _aware(created_at)
    if deadline <= start:
        return None
    return deadline - (deadline - start) * percent / 100


@dataclass
class Item:
    task: STask
    deadline: datetime
    key: str


def due_items(tasks: list, tz_name: str, percent: int, now: datetime) -> list:
    """Pure decision (no database, no sending): which tasks need their reminder now."""
    out = []
    for t in tasks:
        if t.done:
            continue
        dl = deadline_of(t.due_date, tz_name)
        trig = trigger_of(t.created_at, dl, percent)
        if trig is None or not (trig <= now < dl):
            continue
        out.append(Item(t, dl, t.due_date.isoformat()))
    return out


def clean_percent(p: int) -> int:
    return p if p in PERCENTS else 30


async def run_cycle(db: AsyncSession, now: Optional[datetime] = None, only_user: Optional[uuid.UUID] = None, sender: Optional[Callable] = None) -> dict:
    sender = sender or notifier.deliver
    now = now or datetime.now(timezone.utc)
    q = select(Preferences, User).join(User, User.id == Preferences.user_id).where(Preferences.remind_enabled.is_(True))
    if only_user is not None:
        q = q.where(User.id == only_user)
    emails = tasks_sent = failures = 0
    for prefs, user in (await db.execute(q)).all():
        pct = clean_percent(prefs.remind_percent)
        low = now.date() - timedelta(days=2)
        tasks = (await db.scalars(select(STask).where(STask.user_id == user.id, STask.done.is_(False), STask.due_date >= low))).all()
        cand = due_items(tasks, prefs.timezone, pct, now)
        if not cand:
            continue
        existing = {(r.task_id, r.due_key): r for r in (await db.scalars(select(TaskReminder).where(TaskReminder.user_id == user.id, TaskReminder.task_id.in_([c.task.id for c in cand])))).all()}
        claimed = []
        for c in cand[:MAX_PER_EMAIL]:
            prev = existing.get((c.task.id, c.key))
            if prev is None:
                row = TaskReminder(user_id=user.id, task_id=c.task.id, due_key=c.key, percent=pct, status="claiming", attempts=1, created_at=now, updated_at=now)
                db.add(row)
                try:
                    await db.commit()
                except IntegrityError:                      # another scheduler claimed it first: send nothing
                    await db.rollback()
                    continue
                claimed.append((c, row))
            else:
                stale = prev.status == "claiming" and now - _aware(prev.updated_at or prev.created_at) > STALE_CLAIM
                retry = prev.status == "failed" and prev.attempts < MAX_ATTEMPTS and now - _aware(prev.updated_at or prev.created_at) >= RETRY_AFTER
                if not (stale or retry):
                    continue
                res = await db.execute(update(TaskReminder).where(TaskReminder.id == prev.id, TaskReminder.status == prev.status, TaskReminder.attempts == prev.attempts)
                                       .values(status="claiming", attempts=prev.attempts + 1, updated_at=now))
                await db.commit()
                if res.rowcount != 1:
                    continue
                await db.refresh(prev)
                claimed.append((c, prev))
        if not claimed:
            continue
        # last look: a task that was finished or deleted a moment ago must not get an e-mail
        ids = [c.task.id for c, _ in claimed]
        still = set((await db.scalars(select(STask.id).where(STask.id.in_(ids), STask.done.is_(False)))).all())
        send = [(c, r) for c, r in claimed if c.task.id in still]
        for c, r in claimed:
            if c.task.id not in still:
                r.status, r.detail, r.updated_at = "skipped", "finished or deleted", now
        if not send:
            await db.commit()
            continue
        msg = build_task_reminder(user.email, user.display_name, [(c.task.title, c.deadline) for c, _ in send], prefs.timezone, pct, now)
        try:
            mode = await sender(msg)
            status_, detail = ("sent" if mode == "smtp" else "outbox"), ("accepted by the mail server" if mode == "smtp" else "saved as a file; no mail server")
            emails += 1
            tasks_sent += len(send)
        except Exception as exc:  # network or mail-server problems must never crash the job
            code, _ = notifier.classify_mail_error(exc)
            log.warning("Could not send a task reminder: %s (%s)", code, type(exc).__name__)
            status_, detail = "failed", f"error: {code}"[:80]
            failures += 1
        for _, r in send:
            r.status, r.detail, r.updated_at = status_, detail, now
        await db.commit()
    return {"emails": emails, "tasks": tasks_sent, "failures": failures}


async def loop(session_factory, minutes: int) -> None:
    """Background job started with the API. Runs for as long as the backend runs; the browser does not have to be open."""
    import asyncio
    await asyncio.sleep(8)
    while True:
        try:
            async with session_factory() as db:
                res = await run_cycle(db)
                if res["emails"] or res["failures"]:
                    log.info("Task reminder cycle: %s", res)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("Task reminder cycle failed: %s", type(exc).__name__)
        await asyncio.sleep(max(1, minutes) * 60)
