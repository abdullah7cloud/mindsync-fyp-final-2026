"""Reminders v2: lead times, same-day, overdue, time zones, duplicate prevention, rescheduling, failure handling, honest status."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import notifier, reminders
from app.assist.models import ReminderLog, UserSettings
from app.assist.settings_schema import StudySettings
from app.database import Base
from app.models import Task, TaskStatus, User

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def user(alerts=True):
    return User(id=uuid.uuid4(), email=f"{uuid.uuid4().hex[:6]}@example.com", password_hash="x", display_name="Abi", email_alerts=alerts)


def task(u, title, hours, status=TaskStatus.pending, sent=None, now=NOW):
    return Task(id=uuid.uuid4(), owner_id=u.id, title=title, description="", category="general", difficulty=3, deadline=now + timedelta(hours=hours),
                status=status, reminder_sent_at=sent)


class World:
    """An in-memory database plus a fake mail sender that records what was 'sent'."""

    def __init__(self):
        self.sent, self.fail, self.mode = [], None, "smtp"

    async def sender(self, msg):
        if self.fail:
            raise self.fail
        self.sent.append(msg)
        return self.mode


def run_scenario(objs, steps):
    """steps: list of (now, only_user) - runs the cycle at each time on the same database; returns (results, final log rows, tasks, world)."""
    pytest.importorskip("aiosqlite")
    world = World()

    async def go():
        from tests.dbutil import make_engine
        engine = await make_engine()
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        results = []
        async with Session() as db:
            from tests.dbutil import seed
            await seed(db, objs)
            for step in steps:
                if callable(step):
                    await step(db, world)
                    continue
                now = step
                results.append(await reminders.run_cycle(db, now=now, sender=world.sender))
            logs = list((await db.scalars(select(ReminderLog).order_by(ReminderLog.created_at))).all())
            tasks = list((await db.scalars(select(Task))).all())
        await engine.dispose()
        return results, logs, tasks

    results, logs, tasks = asyncio.run(go())
    return results, logs, tasks, world


def settings_row(u, **kw):
    return UserSettings(user_id=u.id, data=StudySettings(**kw).model_dump())


def test_default_behaviour_is_the_old_48_hour_alert_once():
    u = user()
    t = task(u, "essay", 30)
    results, logs, tasks, world = run_scenario([u, t], [NOW, NOW + timedelta(hours=1), NOW + timedelta(hours=2)])
    assert [r["emails"] for r in results] == [1, 0, 0] and len(world.sent) == 1
    assert [l.status for l in logs] == ["sent"] and tasks[0].reminder_sent_at is not None


def test_several_lead_times_each_fire_once_at_their_own_moment():
    u = user()
    t = task(u, "report", 60)                                    # due in 60 h
    st = settings_row(u, remind_lead_hours=[48, 24, 3])
    steps = [NOW,                                                # 60 h left: nothing yet
             NOW + timedelta(hours=13),                          # 47 h left: the 48 h reminder
             NOW + timedelta(hours=14),                          # same lead, no repeat
             NOW + timedelta(hours=37),                          # 23 h left: the 24 h reminder
             NOW + timedelta(hours=58),                          # 2 h left: the 3 h reminder
             NOW + timedelta(hours=58, minutes=30)]
    results, logs, _, world = run_scenario([u, t, st], steps)
    assert [r["emails"] for r in results] == [0, 1, 0, 1, 1, 0]
    assert [l.dedupe_key.split(":")[0] for l in logs] == ["lead48", "lead24", "lead3"]


def test_when_several_leads_are_already_due_one_email_goes_out_and_the_rest_are_logged_as_skipped():
    u = user()
    t = task(u, "short notice", 2)                               # created 2 h before the deadline
    st = settings_row(u, remind_lead_hours=[48, 24, 3])
    results, logs, _, world = run_scenario([u, t, st], [NOW])
    assert results[0]["emails"] == 1 and results[0]["skipped"] == 2 and len(world.sent) == 1
    assert sorted(l.status for l in logs) == ["sent", "skipped", "skipped"]


def test_same_day_reminder_uses_the_students_time_zone_and_hour():
    u = user()
    # 29 Oct 2026, deadline 18:00 UTC = 19:00 in Copenhagen; "now" is 06:30 UTC = 07:30 local (before 08:00) then 07:30 UTC = 08:30 local
    t = task(u, "lab report", 11.5 + 0, now=NOW.replace(hour=6, minute=30))    # deadline 18:00 UTC
    st = settings_row(u, timezone="Europe/Copenhagen", remind_lead_hours=[1], same_day_reminder=True, same_day_hour=8)
    results, logs, _, world = run_scenario([u, t, st], [NOW.replace(hour=6, minute=30), NOW.replace(hour=7, minute=30), NOW.replace(hour=9)])
    assert [r["emails"] for r in results] == [0, 1, 0]
    assert logs[0].kind == "same_day"
    body = world.sent[0].get_body(("plain",)).get_content()
    assert "19:00 Europe/Copenhagen" in body and "Due today" in body


def test_overdue_reminder_is_opt_in_once_and_stops_after_three_days():
    u = user()
    t = task(u, "missed", -5)
    off = run_scenario([u, t], [NOW])[0]
    assert off[0]["emails"] == 0
    u2, t2 = user(), None
    t2 = task(u2, "missed", -5)
    st = settings_row(u2, overdue_reminder=True)
    results, logs, _, world = run_scenario([u2, t2, st], [NOW, NOW + timedelta(hours=1), NOW + timedelta(days=5)])
    assert [r["emails"] for r in results] == [1, 0, 0] and logs[0].kind == "overdue"
    assert "overdue" in world.sent[0]["Subject"]


def test_moving_a_deadline_re_arms_the_reminder():
    u = user()
    t = task(u, "essay", 30)

    async def move_deadline(db, world):
        row = await db.get(Task, t.id)
        row.deadline = NOW + timedelta(hours=40)
        row.reminder_sent_at = None                            # what tasks.py does on a deadline change
        await db.commit()
    results, logs, _, world = run_scenario([u, t], [NOW, move_deadline, NOW + timedelta(hours=1)])
    assert [r["emails"] for r in results] == [1, 1] and len(logs) == 2 and logs[0].dedupe_key != logs[1].dedupe_key


def test_a_second_run_for_the_same_key_cannot_send_twice_even_if_the_flag_is_lost():
    u = user()
    t = task(u, "essay", 30)

    async def lose_flag(db, world):
        row = await db.get(Task, t.id)
        row.reminder_sent_at = None
        await db.commit()
    results, logs, _, world = run_scenario([u, t], [NOW, lose_flag, NOW + timedelta(minutes=20)])
    assert [r["emails"] for r in results] == [1, 0] and len(world.sent) == 1 and len(logs) == 1


def test_failed_sends_are_logged_retried_after_15_minutes_and_given_up_after_5():
    u = user()
    t = task(u, "essay", 30)

    async def down(db, world):
        world.fail = OSError("mail server down")

    async def up(db, world):
        world.fail = None
    steps = [down, NOW, NOW + timedelta(minutes=5)] + [NOW + timedelta(minutes=16 * i) for i in range(1, 8)]
    results, logs, tasks, world = run_scenario([u, t], steps)
    assert logs[0].status == "failed" and logs[0].attempts == 5 and logs[0].detail.startswith("error:") and "mail server down" not in logs[0].detail
    assert tasks[0].reminder_sent_at is None and world.sent == []
    assert results[1]["emails"] == 0 and results[0]["failures"] == 1               # the 5 minute re-check did not retry yet
    # recovery inside the retry window
    u, t = user(), task(user(), "essay", 30)
    t.owner_id = u.id
    results, logs, tasks, world = run_scenario([u, t], [down, NOW, up, NOW + timedelta(minutes=16)])
    assert [r["emails"] for r in results] == [0, 1] and logs[0].status == "sent" and logs[0].attempts == 2


def test_status_is_honest_about_what_happened():
    u = user()
    results, logs, _, world = run_scenario([u, task(u, "essay", 30)], [NOW])
    assert logs[0].status == "sent" and "accepted by the mail server" in logs[0].detail
    u2 = user()
    w_mode = World()
    w_mode.mode = "outbox"

    async def outbox(db, world):
        world.mode = "outbox"
    results, logs, _, world = run_scenario([u2, task(u2, "essay", 30)], [outbox, NOW])
    assert logs[0].status == "outbox" and "saved as a file" in logs[0].detail and "sent" not in logs[0].status


def test_opt_out_and_master_switch_and_completed_tasks_send_nothing():
    a, b, c = user(alerts=False), user(), user()
    objs = [a, task(a, "x", 10), b, task(b, "y", 10), settings_row(b, remind_enabled=False), c, task(c, "z", 10, status=TaskStatus.completed)]
    results, logs, _, world = run_scenario(objs, [NOW])
    assert results[0]["emails"] == 0 and world.sent == [] and logs == []


def test_mixed_reminders_arrive_in_one_email_with_sections():
    u = user()
    objs = [u, task(u, "due soon", 30), task(u, "late one", -4), settings_row(u, overdue_reminder=True)]
    results, logs, _, world = run_scenario(objs, [NOW])
    assert results[0]["emails"] == 1 and results[0]["tasks"] == 2
    body = world.sent[0].get_body(("plain",)).get_content()
    assert body.index("Overdue") < body.index("Due soon") and "late one" in body and "due soon" in body
    assert world.sent[0]["Subject"] == "MindSync: 2 tasks need your attention"


def test_html_in_titles_is_escaped_in_the_new_email():
    u = user()
    objs = [u, task(u, "<img src=x onerror=alert(1)>", 30), settings_row(u, timezone="Asia/Tokyo")]
    _, _, _, world = run_scenario(objs, [NOW])
    html_part = world.sent[0].get_body(("html",)).get_content()
    assert "<img" not in html_part and "&lt;img" in html_part and "Asia/Tokyo" in html_part


# ---------------------------------------------------------------- through the API
def test_status_route_reports_the_settings_and_delivery_note(api):
    u = api.register()
    h = u["headers"]
    api.client.put("/settings", json={"remind_lead_hours": [72, 24], "same_day_reminder": True, "timezone": "Europe/London"}, headers=h)
    s = api.client.get("/notifications/status", headers=h).json()
    assert s["lead_hours"] == [72, 24] and s["same_day"] is True and s["timezone"] == "Europe/London" and "mail server" in s["delivery_note"]
    r = api.client.post("/notifications/test", headers=h).json()
    assert r["mode"] == "outbox"
    log = api.client.get("/assist/reminders", headers=h).json()["items"]
    assert log[0]["kind"] == "test" and log[0]["status"] == "outbox"
    api.client.patch("/notifications/settings", json={"email_alerts": False}, headers=h)
    assert api.client.get("/settings", headers=h).json()["settings"]["remind_enabled"] is False
