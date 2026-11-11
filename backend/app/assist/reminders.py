"""
In-app reminders: one daily study reminder and deadline reminders. Nothing here sends an email or any message outside MindSync.

`compute` is pure: from the roadmap view, the student's settings and the local time it says which reminders should exist right now.
Each reminder has a stable `key`, so the same reminder can never be created twice:

  daily:2026-10-29                          one per day, shown once the student's reminder time has passed
  deadline:<task>:<days>d:<deadline date>   7 / 3 / 1 days before (the student chooses), only the nearest one that is due
  deadline:<task>:today:<deadline date>     on the day
  deadline:<task>:overdue:<deadline date>   once, after the deadline, while work is unfinished

Because the deadline date is part of the key, changing a deadline creates fresh reminders for the new date, and the unread ones for the
old date are removed. The daily reminder of today is refreshed when the plan changes, so it always matches the roadmap.
Email is not implemented: `email_reminders_future` is only a stored wish; `delivery` tells the page so.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User

from . import roadmap_view as RV
from .models import Notification
from .settings_schema import StudySettings

router = APIRouter(prefix="/reminders", tags=["reminders (in the app)"])

KEEP_READ = 60                  # read reminders kept per student (the unread ones are never trimmed)
DELIVERY_NOTE = "Reminders appear inside MindSync. No email or text message is sent in this version."


def _greeting(hhmm: str) -> str:
    h = int(hhmm[:2])
    return "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"


def _short(items: list, n: int = 4) -> str:
    parts = [f"{i['title']} ({i['minutes']} min)" for i in items[:n]]
    return "; ".join(parts) + (f"; and {len(items) - n} more" if len(items) > n else "")


def summary_for(view: dict, today: date) -> dict:
    cards = view["tasks"]
    count = lambda st: sum(1 for c in cards if c["state"] == st)
    ti = [i for i in view["today_items"] if i["status"] not in ("done", "partial")]
    return {"today_blocks": len(view["today_items"]), "today_left": len(ti), "today_minutes": sum(i["minutes"] for i in view["today_items"]),
            "tomorrow_blocks": len(view["tomorrow_items"]), "tomorrow_minutes": sum(i["minutes"] for i in view["tomorrow_items"]),
            "overdue_blocks": len(view["overdue"]), "deadlines": {"upcoming": count("upcoming"), "due_today": count("due_today"), "overdue": count("overdue"),
                                                                    "completed": count("completed")},
            "soonest": next(({"title": c["title"], "days_left": c["days_left"], "deadline": c["deadline"]} for c in cards if c["state"] in ("upcoming", "due_today", "overdue")), None),
            "delivery": "in_app", "delivery_note": DELIVERY_NOTE}


def _when(days_left: int) -> str:
    return "today" if days_left == 0 else "tomorrow" if days_left == 1 else f"in {days_left} days" if days_left > 0 else (
        "yesterday" if days_left == -1 else f"{-days_left} days ago")


def compute(view: dict, st: StudySettings, now: datetime, name: str = "") -> list:
    """The reminders that should exist at `now` (student's local time). Returns [{key, kind, title, body, task_id, due_on, data}]."""
    if not st.inapp_reminders:
        return []
    today = now.date()
    out = []
    if st.daily_reminder and view["summary"]["has_roadmap"] and now.strftime("%H:%M") >= st.daily_reminder_time:
        t_items = [i for i in view["today_items"] if i["status"] != "skipped"]
        m_items = view["tomorrow_items"]
        lines = []
        if t_items:
            left = [i for i in t_items if i["status"] not in ("done", "partial")]
            lines.append(f"Today: {_short(left) if left else 'everything is already confirmed. Well done.'}")
        else:
            lines.append("Today: no study blocks planned. A rest day is part of a good plan.")
        if m_items:
            lines.append(f"Tomorrow: {len(m_items)} block{'s' if len(m_items) != 1 else ''}, {sum(i['minutes'] for i in m_items)} minutes.")
        if view["overdue"]:
            lines.append(f"{len(view['overdue'])} earlier block{'s' if len(view['overdue']) != 1 else ''} not finished yet. You can replan them in My Tasks.")
        lines.append(f"Time zone: {st.timezone}.")
        title = f"{_greeting(st.daily_reminder_time)}{', ' + name if name else ''}! Your study plan for today"
        out.append({"key": f"daily:{today.isoformat()}", "kind": "daily", "title": title[:200], "body": " ".join(lines)[:600], "task_id": None, "due_on": today,
                    "data": {"link": "/tasks", "today": [{"id": i["id"], "title": i["title"], "minutes": i["minutes"], "status": i["status"]} for i in t_items][:12],
                             "tomorrow": [{"id": i["id"], "title": i["title"], "minutes": i["minutes"]} for i in m_items][:12], "overdue": len(view["overdue"]),
                             "time_zone": st.timezone}})
    leads = sorted(set(st.deadline_days))
    for c in view["tasks"]:
        if c["state"] == "completed" or not c["deadline"]:
            continue
        dl, dl_days = c["deadline"], c["days_left"]
        left_min = c.get("unfinished_minutes") or 0
        base = f"deadline:{c['task_id']}"
        tail = f" {left_min} minutes of planned work are still open." if left_min else ""
        if dl_days < 0:
            if st.deadline_overdue:
                out.append({"key": f"{base}:overdue:{dl}", "kind": "deadline", "title": f"Overdue: {c['title']}"[:200],
                            "body": f"The deadline was {_when(dl_days)} ({dl}).{tail} Your work stays on your list; open My Tasks to replan it."[:600],
                            "task_id": c["task_id"], "due_on": date.fromisoformat(dl), "data": {"link": "/tasks", "state": "overdue", "days_left": dl_days}})
        elif dl_days == 0:
            if st.deadline_on_day:
                out.append({"key": f"{base}:today:{dl}", "kind": "deadline", "title": f"Due today: {c['title']}"[:200], "body": f"This is due today ({dl}).{tail}"[:600],
                            "task_id": c["task_id"], "due_on": date.fromisoformat(dl), "data": {"link": "/tasks", "state": "due_today", "days_left": 0}})
        else:
            due = [d for d in leads if dl_days <= d]
            if due:
                d = min(due)
                out.append({"key": f"{base}:{d}d:{dl}", "kind": "deadline", "title": f"Deadline {_when(dl_days)}: {c['title']}"[:200],
                            "body": f"Due on {dl}.{tail} You have confirmed {c['percent']}% of the planned work."[:600], "task_id": c["task_id"],
                            "due_on": date.fromisoformat(dl), "data": {"link": "/tasks", "state": "upcoming", "days_left": dl_days}})
    return out


# ---------------------------------------------------------------- database side
def _view(n: Notification) -> dict:
    return {"id": str(n.id), "kind": n.kind, "title": n.title, "body": n.body, "task_id": str(n.task_id) if n.task_id else None,
            "due_on": n.due_on.isoformat() if n.due_on else None, "data": n.data or {}, "created_at": n.created_at.isoformat(), "read": n.read_at is not None}


async def sync(db: AsyncSession, user: User, desired: list) -> list:
    """Create what is missing, refresh what changed, drop unread reminders that no longer apply. Safe to call on every page view."""
    rows = (await db.scalars(select(Notification).where(Notification.user_id == user.id))).all()
    have = {n.key: n for n in rows}
    want = {d["key"]: d for d in desired}
    changed = False
    for key, d in want.items():
        tid = uuid.UUID(d["task_id"]) if d["task_id"] else None
        n = have.get(key)
        if n is None:
            n = Notification(user_id=user.id, kind=d["kind"], key=key, title=d["title"], body=d["body"], task_id=tid, due_on=d["due_on"], data=d["data"])
            db.add(n)
            have[key] = n
            changed = True
        elif (n.title, n.body, n.data) != (d["title"], d["body"], d["data"]):
            n.title, n.body, n.data = d["title"], d["body"], d["data"]
            changed = True
    for key, n in list(have.items()):
        if n.kind == "deadline" and key not in want and n.read_at is None:
            await db.delete(n)               # the deadline moved, the task was finished or removed, or a closer reminder took over
            del have[key]
            changed = True
    read = sorted((n for n in have.values() if n.read_at is not None), key=lambda n: n.created_at, reverse=True)
    for n in read[KEEP_READ:]:
        await db.delete(n)
        have.pop(n.key, None)
        changed = True
    if changed:
        await db.commit()
    return sorted(have.values(), key=lambda n: n.created_at, reverse=True)


@router.get("")
async def list_reminders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    from . import roadmap as RDM
    from . import store
    core = await store.load_core(db, user)
    view = await RDM.full_view(db, user, core)
    items = await sync(db, user, compute(view, core.settings, core.now, user.display_name.split(" ")[0] if user.display_name else ""))
    out = [_view(n) for n in items][:40]
    return {"items": out, "unread": sum(1 for n in items if n.read_at is None), "summary": view["reminders"], "time_zone": core.settings.timezone,
            "delivery": "in_app", "delivery_note": DELIVERY_NOTE,
            "email_available": False, "email_note": "Email reminders are not available in this version."}


@router.post("/{reminder_id}/read")
async def mark_read(reminder_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    try:
        n = await db.get(Notification, uuid.UUID(reminder_id))
    except ValueError:
        n = None
    if n is None or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found")
    n.read_at = n.read_at or datetime.now(timezone.utc)
    await db.commit()
    return {"saved": True}


@router.post("/read-all")
async def read_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    for n in (await db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)))).all():
        n.read_at = now
    await db.commit()
    return {"saved": True}
