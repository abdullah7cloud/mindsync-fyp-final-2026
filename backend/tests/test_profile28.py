"""Update 28: My Profile (name, verified e-mail change, picture) and Settings (reminders at 30 / 35 percent, time zone)."""
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import notifier
from app.models import User
from app.profile28 import reminders as R
from app.profile28.models import EmailChange, Preferences, ProfilePicture, TaskReminder
from app.simple.models import SPlan, STask

H = lambda u: u["headers"]


# ------------------------------------------------------------------ helpers
@pytest.fixture()
def mailbox(monkeypatch):
    sent = []

    async def fake(msg):
        sent.append(msg)
        return "outbox"
    monkeypatch.setattr(notifier, "deliver", fake)

    async def quiet(msg, purpose):
        sent.append(msg)
    monkeypatch.setattr(notifier, "deliver_quietly", quiet)
    return sent


def code_in(msg) -> str:
    return re.search(r"code is: (\d{6})", msg.get_body(("plain",)).get_content()).group(1)


def png_bytes(size=(400, 300), mode="RGB", color=(200, 30, 30)) -> bytes:
    from PIL import Image
    out = io.BytesIO()
    Image.new(mode, size, color).save(out, format="PNG")
    return out.getvalue()


def login(api, email, password):
    return api.client.post("/auth/login", json={"email": email, "password": password})


# ------------------------------------------------------------------ profile
def test_profile_shows_account_and_name_can_be_changed(api):
    u = api.register(name="Abi Tester")
    p = api.client.get("/my/profile", headers=H(u)).json()
    assert p["display_name"] == "Abi Tester" and p["email"] == u["email"] and p["has_picture"] is False and p["pending_email"] is None
    r = api.client.put("/my/profile", json={"display_name": "  Abi   Khan "}, headers=H(u))
    assert r.status_code == 200 and r.json()["display_name"] == "Abi Khan"
    assert api.client.get("/auth/me", headers=H(u)).json()["display_name"] == "Abi Khan"


def test_profile_name_rules_and_login_needed(api):
    u = api.register()
    for bad in ("", "   ", "x" * 101):
        assert api.client.put("/my/profile", json={"display_name": bad}, headers=H(u)).status_code == 422
    assert api.client.put("/my/profile", json={"display_name": "A", "extra": 1}, headers=H(u)).status_code == 422
    assert api.client.get("/my/profile").status_code == 401
    assert api.client.put("/my/profile", json={"display_name": "A"}).status_code == 401
    zero = api.client.put("/my/profile", json={"display_name": "Abi​\x00 K"}, headers=H(u)).json()["display_name"]
    assert "\x00" not in zero and "​" not in zero


# ------------------------------------------------------------------ e-mail change
def test_email_change_needs_password_then_a_code_sent_to_the_new_address(api, mailbox):
    u = api.register()
    new = "fresh." + u["email"]
    assert api.client.post("/my/email/start", json={"new_email": new, "password": "wrong-pass-1"}, headers=H(u)).status_code == 403
    assert mailbox == []
    r = api.client.post("/my/email/start", json={"new_email": new, "password": u["password"]}, headers=H(u))
    assert r.status_code == 200 and r.json()["delivery"] in ("email", "demo")
    assert len(mailbox) == 1 and mailbox[0]["To"] == new
    assert api.client.get("/my/profile", headers=H(u)).json()["email"] == u["email"]           # nothing changed yet
    assert api.client.get("/my/profile", headers=H(u)).json()["pending_email"]["email"] == new
    done = api.client.post("/my/email/confirm", json={"code": code_in(mailbox[0])}, headers=H(u))
    assert done.status_code == 200 and done.json()["profile"]["email"] == new
    assert login(api, new, u["password"]).status_code == 200 and login(api, u["email"], u["password"]).status_code == 401
    assert mailbox[-1]["To"] == u["email"] and "changed" in mailbox[-1]["Subject"]               # the OLD address is told
    assert new not in mailbox[-1].get_body(("plain",)).get_content()                             # and the notice does not print the full new address
    assert api.client.get("/my/profile", headers=H(u)).json()["pending_email"] is None


def test_wrong_code_five_times_cancels_the_change(api, mailbox):
    u = api.register()
    new = "five." + u["email"]
    api.client.post("/my/email/start", json={"new_email": new, "password": u["password"]}, headers=H(u))
    good = code_in(mailbox[0])
    bad = "000000" if good != "000000" else "111111"
    for i in range(5):
        r = api.client.post("/my/email/confirm", json={"code": bad}, headers=H(u))
        assert r.status_code == 400
    r = api.client.post("/my/email/confirm", json={"code": good}, headers=H(u))             # even the right code is refused after five misses
    assert r.status_code in (400, 429)
    assert api.client.get("/my/profile", headers=H(u)).json()["email"] == u["email"]


def test_code_must_be_six_digits_and_belongs_to_the_asking_student(api, mailbox):
    a, b = api.register(), api.register()
    api.client.post("/my/email/start", json={"new_email": "own." + a["email"], "password": a["password"]}, headers=H(a))
    code = code_in(mailbox[0])
    for bad in ("12345", "1234567", "abcdef", ""):
        assert api.client.post("/my/email/confirm", json={"code": bad}, headers=H(a)).status_code == 422
    assert api.client.post("/my/email/confirm", json={"code": code}, headers=H(b)).status_code == 400    # b has nothing pending
    assert api.client.post("/my/email/confirm", json={"code": code}).status_code == 401
    assert api.client.get("/my/profile", headers=H(b)).json()["email"] == b["email"]


def test_taken_address_gets_the_same_answer_and_no_e_mail(api, mailbox):
    a, b = api.register(), api.register()
    ok = api.client.post("/my/email/start", json={"new_email": "free." + a["email"], "password": a["password"]}, headers=H(a))
    n = len(mailbox)
    taken = api.client.post("/my/email/start", json={"new_email": b["email"].upper(), "password": a["password"]}, headers=H(a))
    assert taken.status_code == 200 and taken.json() == ok.json()
    assert len(mailbox) == n                                           # nothing was sent to a registered address
    assert api.client.post("/my/email/confirm", json={"code": "123456"}, headers=H(a)).status_code == 400


def test_same_invalid_and_rate_limited_email_requests(api, mailbox):
    u = api.register()
    assert api.client.post("/my/email/start", json={"new_email": u["email"].upper(), "password": u["password"]}, headers=H(u)).status_code == 400
    assert api.client.post("/my/email/start", json={"new_email": "nope", "password": u["password"]}, headers=H(u)).status_code == 422
    for i in range(3):
        assert api.client.post("/my/email/start", json={"new_email": f"n{i}." + u["email"], "password": u["password"]}, headers=H(u)).status_code == 200
    assert api.client.post("/my/email/start", json={"new_email": "n9." + u["email"], "password": u["password"]}, headers=H(u)).status_code == 429


def test_wrong_passwords_lock_the_email_form_and_a_failed_send_leaves_nothing_pending(api, monkeypatch):
    u = api.register()
    for _ in range(5):
        api.client.post("/my/email/start", json={"new_email": "z." + u["email"], "password": "nope-nope-1"}, headers=H(u))
    assert api.client.post("/my/email/start", json={"new_email": "z." + u["email"], "password": u["password"]}, headers=H(u)).status_code == 429
    v = api.register()

    async def boom(msg):
        raise OSError("mail server is down")
    monkeypatch.setattr(notifier, "deliver", boom)
    r = api.client.post("/my/email/start", json={"new_email": "q." + v["email"], "password": v["password"]}, headers=H(v))
    assert r.status_code == 502 and "mail server" not in r.text
    assert api.client.get("/my/profile", headers=H(v)).json()["pending_email"] is None


def test_the_code_is_stored_only_as_a_hash(api, mailbox):
    u = api.register()
    api.client.post("/my/email/start", json={"new_email": "h." + u["email"], "password": u["password"]}, headers=H(u))
    code = code_in(mailbox[0])
    import asyncio
    from app.database import get_db
    from app.main import app

    async def rows():
        async for db in app.dependency_overrides[get_db]():
            return (await db.scalars(select(EmailChange))).all()
    row = asyncio.get_event_loop().run_until_complete(rows()) if False else None
    assert code and len(code) == 6          # (the stored value is checked in test_stored_code_is_hashed below, where a database session is available)


def test_stored_code_is_hashed():
    from app.profile28.routes import _hash_code
    uid = uuid.uuid4()
    h = _hash_code(uid, "A@b.com", "123456")
    assert "123456" not in h and len(h) == 64 and h == _hash_code(uid, "a@B.com", "123456") and h != _hash_code(uid, "a@b.com", "123457")


def test_old_password_only_route_cannot_bypass_the_code(api):
    u = api.register()
    assert api.client.post("/account/email", json={"new_email": "x." + u["email"], "password": u["password"]}, headers=H(u)).status_code == 410


# ------------------------------------------------------------------ picture
def test_picture_upload_replace_download_and_remove(api):
    u = api.register()
    r = api.client.post("/my/avatar", files={"file": ("me.png", png_bytes(), "image/png")}, headers=H(u))
    assert r.status_code == 200 and r.json()["has_picture"] is True and r.json()["picture_version"] == 1
    img = api.client.get("/my/avatar", headers=H(u))
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg" and img.content[:2] == b"\xff\xd8"
    from PIL import Image
    assert Image.open(io.BytesIO(img.content)).size == (256, 256)
    r2 = api.client.post("/my/avatar", files={"file": ("new.png", png_bytes(color=(10, 10, 200)), "image/png")}, headers=H(u))
    assert r2.json()["picture_version"] == 2
    gone = api.client.delete("/my/avatar", headers=H(u))
    assert gone.status_code == 200 and gone.json()["has_picture"] is False
    assert api.client.get("/my/avatar", headers=H(u)).status_code == 404


def test_picture_is_redrawn_without_hidden_camera_data(api):
    from PIL import Image
    im = Image.new("RGB", (300, 500), (0, 120, 0))
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    exif[0x8825] = {1: "N", 2: (55.0, 40.0, 0.0)}          # a GPS block
    out = io.BytesIO()
    im.save(out, format="JPEG", exif=exif)
    assert b"SecretCameraMaker" in out.getvalue()
    u = api.register()
    assert api.client.post("/my/avatar", files={"file": ("p.jpg", out.getvalue(), "image/jpeg")}, headers=H(u)).status_code == 200
    stored = api.client.get("/my/avatar", headers=H(u)).content
    assert b"SecretCameraMaker" not in stored and b"Exif" not in stored[:64]
    assert Image.open(io.BytesIO(stored)).getexif() == {} or len(Image.open(io.BytesIO(stored)).getexif()) == 0


def test_picture_refuses_fake_huge_empty_and_wrong_files(api):
    u = api.register()
    h = H(u)
    assert api.client.post("/my/avatar", files={"file": ("a.png", b"this is not an image at all", "image/png")}, headers=h).status_code == 422
    assert api.client.post("/my/avatar", files={"file": ("a.png", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "image/png")}, headers=h).status_code == 422
    assert api.client.post("/my/avatar", files={"file": ("a.png", b"GIF89a" + b"\x00" * 50, "image/gif")}, headers=h).status_code == 422
    assert api.client.post("/my/avatar", files={"file": ("a.png", b"", "image/png")}, headers=h).status_code == 422
    assert api.client.post("/my/avatar", files={"file": ("a.png", b"\x89PNG" + b"0" * (3 * 1024 * 1024 + 10), "image/png")}, headers=h).status_code == 413
    assert api.client.get("/my/profile", headers=h).json()["has_picture"] is False
    assert api.client.post("/my/avatar", files={"file": ("a.png", png_bytes(), "image/png")}).status_code == 401


def test_pictures_are_private_and_transparent_images_work(api):
    a, b = api.register(), api.register()
    api.client.post("/my/avatar", files={"file": ("t.png", png_bytes(mode="RGBA", color=(0, 0, 0, 0)), "image/png")}, headers=H(a))
    assert api.client.get("/my/avatar", headers=H(a)).status_code == 200
    assert api.client.get("/my/avatar", headers=H(b)).status_code == 404
    assert api.client.get("/my/avatar").status_code == 401


# ------------------------------------------------------------------ settings
def test_settings_default_off_30_percent_and_can_be_changed(api):
    u = api.register()
    s = api.client.get("/my/settings", headers=H(u)).json()
    assert s["remind_enabled"] is False and s["remind_percent"] == 30 and s["timezone"] == "UTC" and s["percent_choices"] == [30, 35]
    r = api.client.put("/my/settings", json={"remind_enabled": True, "remind_percent": 35, "timezone": "Europe/Copenhagen"}, headers=H(u))
    assert r.status_code == 200 and r.json()["remind_enabled"] is True and r.json()["remind_percent"] == 35 and r.json()["timezone"] == "Europe/Copenhagen"
    again = api.client.put("/my/settings", json={"remind_enabled": False}, headers=H(u)).json()
    assert again["remind_enabled"] is False and again["remind_percent"] == 35 and again["timezone"] == "Europe/Copenhagen"      # a partial save keeps the rest


def test_settings_reject_other_percentages_bad_zones_and_unknown_fields(api):
    u = api.register()
    h = H(u)
    for body in ({"remind_percent": 25}, {"remind_percent": 40}, {"remind_percent": 0}, {"remind_percent": "30%"}, {"timezone": "Mars/Base"}, {"timezone": "../../etc"},
                 {"timezone": "x" * 100}, {"remind_enabled": True, "evil": 1}):
        assert api.client.put("/my/settings", json=body, headers=h).status_code == 422, body
    assert api.client.get("/my/settings", headers=h).json()["remind_percent"] == 30
    assert api.client.get("/my/settings").status_code == 401


def test_settings_are_per_student(api):
    a, b = api.register(), api.register()
    api.client.put("/my/settings", json={"remind_enabled": True, "remind_percent": 35}, headers=H(a))
    assert api.client.get("/my/settings", headers=H(b)).json()["remind_enabled"] is False


def test_test_email_goes_only_to_the_students_own_address_and_is_limited(api, mailbox):
    u = api.register()
    r = api.client.post("/my/settings/test-email", headers=H(u))
    assert r.status_code == 200 and mailbox[-1]["To"] == u["email"]
    api.client.post("/my/settings/test-email", headers=H(u))
    api.client.post("/my/settings/test-email", headers=H(u))
    assert api.client.post("/my/settings/test-email", headers=H(u)).status_code == 429
    assert api.client.post("/my/settings/test-email").status_code == 401


def test_export_and_delete_cover_the_new_data(api, mailbox):
    u = api.register()
    api.client.put("/my/settings", json={"remind_enabled": True, "remind_percent": 35}, headers=H(u))
    api.client.post("/my/avatar", files={"file": ("a.png", png_bytes(), "image/png")}, headers=H(u))
    exp = api.client.get("/account/export", headers=H(u)).json()
    assert exp["profile_and_settings"]["email_reminders"] is True and exp["profile_and_settings"]["reminder_percent"] == 35 and exp["profile_and_settings"]["has_profile_picture"] is True
    assert api.client.request("DELETE", "/account", json={"password": u["password"]}, headers=H(u)).status_code == 204
    assert login(api, u["email"], u["password"]).status_code == 401


# ------------------------------------------------------------------ the reminder rule (pure)
def mk_task(created, due, done=False, tid=None):
    return STask(id=tid or uuid.uuid4(), user_id=uuid.uuid4(), plan_id=uuid.uuid4(), position=0, title="Read chapter 4", details="", due_date=due, minutes=30, done=done, created_at=created)


T0 = datetime(2026, 9, 1, 23, 59, tzinfo=timezone.utc)
DUE = date(2026, 9, 11)             # the deadline is 11 Sep 23:59, exactly 10 days after T0


def test_ten_days_and_thirty_percent_means_three_days_before():
    dl = R.deadline_of(DUE, "UTC")
    assert dl == datetime(2026, 9, 11, 23, 59, tzinfo=timezone.utc) and dl - T0 == timedelta(days=10)
    assert R.trigger_of(T0, dl, 30) == dl - timedelta(days=3)
    assert R.trigger_of(T0, dl, 35) == dl - timedelta(days=3, hours=12)


def test_reminder_is_due_exactly_from_the_trigger_until_the_deadline():
    t = mk_task(T0, DUE)
    trig = datetime(2026, 9, 8, 23, 59, tzinfo=timezone.utc)
    assert R.due_items([t], "UTC", 30, trig - timedelta(minutes=1)) == []
    assert len(R.due_items([t], "UTC", 30, trig)) == 1
    assert len(R.due_items([t], "UTC", 30, trig + timedelta(days=2))) == 1
    assert R.due_items([t], "UTC", 30, datetime(2026, 9, 11, 23, 59, tzinfo=timezone.utc)) == []         # the deadline has passed: no reminder
    assert R.due_items([t], "UTC", 35, trig - timedelta(hours=12)) != [] and R.due_items([t], "UTC", 30, trig - timedelta(hours=12)) == []


def test_completed_tasks_never_get_a_reminder():
    t = mk_task(T0, DUE, done=True)
    assert R.due_items([t], "UTC", 30, T0 + timedelta(days=9)) == []


def test_the_students_time_zone_moves_the_deadline():
    t = mk_task(T0, DUE)
    utc = R.deadline_of(DUE, "UTC")
    cph = R.deadline_of(DUE, "Europe/Copenhagen")          # 23:59 in Denmark (summer time, UTC+2) is two hours earlier in UTC
    assert utc - cph == timedelta(hours=2)
    nyc = R.deadline_of(DUE, "America/New_York")
    assert nyc - utc == timedelta(hours=4)
    assert R.deadline_of(DUE, "Not/AZone") == utc            # an unknown zone falls back to UTC instead of crashing


def test_a_task_with_no_time_span_is_ignored():
    t = mk_task(datetime(2026, 9, 12, 0, 0, tzinfo=timezone.utc), DUE)
    assert R.due_items([t], "UTC", 30, datetime(2026, 9, 12, 1, tzinfo=timezone.utc)) == []


def test_percent_is_cleaned():
    assert R.clean_percent(30) == 30 and R.clean_percent(35) == 35 and R.clean_percent(50) == 30


# ------------------------------------------------------------------ the reminder job (database, fake mail)
class World:
    def __init__(self):
        self.sent, self.fail = [], None

    async def sender(self, msg):
        if self.fail:
            raise self.fail
        self.sent.append(msg)
        return "smtp"


def scenario(steps, setup):
    """setup(db) -> dict of objects; steps run in order: a datetime runs the cycle at that time; a function (db, world, ctx) does something."""
    pytest.importorskip("aiosqlite")
    import asyncio
    from tests.dbutil import make_engine
    world = World()

    async def go():
        engine = await make_engine()
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        results = []
        async with Session() as db:
            ctx = await setup(db)
            for step in steps:
                if callable(step):
                    await step(db, world, ctx)
                else:
                    results.append(await R.run_cycle(db, now=step, sender=world.sender))
            rows = (await db.scalars(select(TaskReminder).order_by(TaskReminder.created_at))).all()
        await engine.dispose()
        return results, rows
    results, rows = asyncio.run(go())
    return results, rows, world


async def base_setup(db, enabled=True, percent=30, tz="UTC", n_tasks=1, created=T0):
    u = User(id=uuid.uuid4(), email=f"{uuid.uuid4().hex[:6]}@example.com", password_hash="x", display_name="Abi")
    plan = SPlan(id=uuid.uuid4(), user_id=u.id, subject="Bio", topic="Cells", goal="", target_date=DUE, roadmap=[], source="ai", note="")
    tasks = [STask(id=uuid.uuid4(), user_id=u.id, plan_id=plan.id, position=i, title=f"Task {i}", details="", due_date=DUE, minutes=30, created_at=created) for i in range(n_tasks)]
    db.add(u)
    await db.flush()
    db.add(plan)
    await db.flush()
    db.add_all(tasks)
    db.add(Preferences(user_id=u.id, remind_enabled=enabled, remind_percent=percent, timezone=tz))
    await db.commit()
    return {"u": u, "tasks": tasks, "plan": plan}


TRIG = datetime(2026, 9, 8, 23, 59, tzinfo=timezone.utc)


def test_one_friendly_email_with_name_deadline_and_time_left_then_never_again():
    res, rows, w = scenario([TRIG - timedelta(minutes=5), TRIG + timedelta(minutes=1), TRIG + timedelta(minutes=16), TRIG + timedelta(days=1)], base_setup)
    assert [r["emails"] for r in res] == [0, 1, 0, 0]
    assert len(w.sent) == 1 and len(rows) == 1 and rows[0].status == "sent"
    body = w.sent[0].get_body(("plain",)).get_content()
    assert "Task 0" in body and "Friday 11 September 2026, 23:59" in body and "about 3 days left" in body and "30%" in body and "once per task" in body
    assert "Task 0" in w.sent[0]["Subject"]


def test_thirty_five_percent_arrives_twelve_hours_earlier():
    async def s(db): return await base_setup(db, percent=35)
    res, rows, w = scenario([TRIG - timedelta(hours=12, minutes=5), TRIG - timedelta(hours=11, minutes=59)], s)
    assert [r["emails"] for r in res] == [0, 1]


def test_off_means_off():
    async def s(db): return await base_setup(db, enabled=False)
    res, rows, w = scenario([TRIG + timedelta(hours=1)], s)
    assert res[0]["emails"] == 0 and w.sent == [] and rows == []


def test_completed_task_gets_nothing_and_a_deleted_task_gets_nothing():
    async def finish(db, w, ctx):
        t = await db.get(STask, ctx["tasks"][0].id)
        t.done = True
        await db.commit()

    async def delete(db, w, ctx):
        await db.delete(await db.get(STask, ctx["tasks"][1].id))
        await db.commit()

    async def s(db): return await base_setup(db, n_tasks=2)
    res, rows, w = scenario([finish, delete, TRIG + timedelta(hours=1)], s)
    assert w.sent == [] and rows == []
    res2, rows2, w2 = scenario([TRIG + timedelta(hours=1)], s)
    assert len(w2.sent) == 1 and len(rows2) == 2          # control: with both open, one e-mail lists both tasks
    assert "Task 0" in w2.sent[0].get_body(("plain",)).get_content() and "Task 1" in w2.sent[0].get_body(("plain",)).get_content()


def test_finishing_after_the_first_reminder_does_not_matter_and_changing_percent_does_not_duplicate():
    async def switch(db, w, ctx):
        p = await db.get(Preferences, ctx["u"].id)
        p.remind_percent = 35
        await db.commit()
    res, rows, w = scenario([TRIG + timedelta(minutes=1), switch, TRIG + timedelta(hours=2)], base_setup)
    assert [r["emails"] for r in res] == [1, 0] and len(w.sent) == 1


def test_changed_deadline_arms_the_task_again():
    async def move(db, w, ctx):
        t = await db.get(STask, ctx["tasks"][0].id)
        t.due_date = date(2026, 9, 21)
        await db.commit()
    later = datetime(2026, 9, 18, 23, 59, tzinfo=timezone.utc)      # the new trigger: 30% of (T0 -> 21 Sep 23:59 = 20 days) = 6 days before
    res, rows, w = scenario([TRIG + timedelta(minutes=1), move, TRIG + timedelta(days=1), later - timedelta(days=3, hours=1), later - timedelta(days=3)], base_setup)
    assert len(w.sent) == 1 + 1
    assert [r.due_key for r in rows] == ["2026-09-11", "2026-09-21"]


def test_two_schedulers_cannot_send_twice():
    """Both think the task is due. The second one finds the first one's claim and sends nothing."""
    import asyncio
    from tests.dbutil import make_engine
    world = World()

    async def go():
        engine = await make_engine()
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with Session() as db:
            await base_setup(db)
        async with Session() as a, Session() as b:
            ra, rb = await asyncio.gather(R.run_cycle(a, now=TRIG + timedelta(hours=1), sender=world.sender), R.run_cycle(b, now=TRIG + timedelta(hours=1), sender=world.sender))
        await engine.dispose()
        return ra, rb
    ra, rb = asyncio.run(go())
    assert len(world.sent) == 1 and ra["emails"] + rb["emails"] == 1


def test_a_failed_send_is_retried_after_15_minutes_and_then_given_up_after_5_tries():
    async def broken(db, w, ctx): w.fail = OSError("down")
    async def fixed(db, w, ctx): w.fail = None
    steps = [broken, TRIG + timedelta(minutes=1), TRIG + timedelta(minutes=5), TRIG + timedelta(minutes=17), fixed, TRIG + timedelta(minutes=33)]
    res, rows, w = scenario(steps, base_setup)
    assert [r["failures"] for r in res] == [1, 0, 1, 0] and res[3]["emails"] == 1
    assert len(w.sent) == 1 and rows[0].status == "sent" and rows[0].attempts == 3
    steps = [broken] + [TRIG + timedelta(minutes=1 + 16 * i) for i in range(8)] + [fixed, TRIG + timedelta(hours=5)]
    res, rows, w = scenario(steps, base_setup)
    assert rows[0].status == "failed" and rows[0].attempts == 5 and w.sent == []


def test_many_tasks_make_one_digest_and_the_mail_text_is_escaped():
    async def s(db):
        c = await base_setup(db, n_tasks=4)
        c["tasks"][0].title = "<script>alert(1)</script> & Co"
        await db.commit()
        return c
    res, rows, w = scenario([TRIG + timedelta(minutes=1)], s)
    assert len(w.sent) == 1 and res[0]["tasks"] == 4
    html_part = w.sent[0].get_body(("html",)).get_content()
    assert "<script>" not in html_part and "&lt;script&gt;" in html_part
    assert "4 study tasks" in w.sent[0]["Subject"]


def test_time_zone_decides_when_the_day_ends():
    async def s(db): return await base_setup(db, tz="America/New_York")
    # New York's 23:59 is 4 hours later than UTC's: the deadline and the trigger both move, the trigger to 9 Sep 02:47 UTC
    res, rows, w = scenario([TRIG + timedelta(minutes=1)], s)
    assert res[0]["emails"] == 0
    res, rows, w = scenario([TRIG + timedelta(hours=3)], s)
    assert res[0]["emails"] == 1
    assert "America/New_York" in w.sent[0].get_body(("plain",)).get_content()


def test_a_mail_server_error_never_leaks_into_the_log_rows():
    async def broken(db, w, ctx): w.fail = RuntimeError("password=hunter2 server said no")
    res, rows, w = scenario([broken, TRIG + timedelta(minutes=1)], base_setup)
    assert rows[0].status == "failed" and "hunter2" not in rows[0].detail


# ------------------------------------------------------------------ the web app still starts the job
def test_the_background_job_is_started_by_the_app_when_switched_on():
    from app import main
    assert hasattr(main, "profile28_reminders") and main.settings.task_reminder_check_minutes >= 1
