"""
Live test of MindSync's REAL e-mail code (smtplib, the reminder cycle, the database) against a local mail server that only collects mail.

Nothing is sent to the internet and nobody is e-mailed. It starts a small SMTP receiver on 127.0.0.1:8025 (package aiosmtpd) and a throw-away
SQLite database, then drives the reminder cycle at chosen moments in time and checks what arrives: lead times, time zones, the same-day and
overdue reminders, duplicate prevention, rescheduling, retry after a failure, a refused login, opt-outs, and hostile task titles.

    pip install aiosmtpd          (test-only; it is in requirements-train.txt, not needed to run MindSync)
    python -m scripts.email_integration_probe

It proves MindSync's side only. Whether a real provider such as Gmail accepts and delivers the message must still be checked once with
test-email.bat and your own App password. Writes docs/email_integration_results.md.
"""
import asyncio
import email
import email.policy
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "probe-secret-probe-secret-probe-secret-123")

from aiosmtpd.controller import Controller                      # noqa: E402
from aiosmtpd.smtp import AuthResult                             # noqa: E402
from sqlalchemy import select                                    # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app import notifier, reminders                              # noqa: E402
from app.assist.models import ReminderLog, UserSettings          # noqa: E402
from app.config import settings                                  # noqa: E402
from app.database import Base                                    # noqa: E402
from app.models import Task, TaskStatus, User                    # noqa: E402

PORT = 8025
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


class Sink:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append((envelope.rcpt_tos, email.message_from_bytes(envelope.content, policy=email.policy.default)))
        return "250 OK"


def start_sink(auth=False):
    sink = Sink()
    kw = {}
    if auth:
        def authenticator(server, session, envelope, mechanism, auth_data):
            return AuthResult(success=False, handled=False)
        kw = dict(authenticator=authenticator, auth_required=True, auth_require_tls=False)
    ctl = Controller(sink, hostname="127.0.0.1", port=PORT, **kw)
    ctl.start()
    return ctl, sink


def body_of(msg):
    part = msg.get_body(("plain",))
    return part.get_content() if part else ""


def mk_user(tag, alerts=True):
    return User(id=uuid.uuid4(), email=f"{tag}-{uuid.uuid4().hex[:5]}@example.com", password_hash="x", display_name=tag, email_alerts=alerts)


def mk_task(u, title, deadline, status=TaskStatus.pending):
    return Task(id=uuid.uuid4(), owner_id=u.id, title=title, description="", category="general", difficulty=3, deadline=deadline, status=status)


def mk_set(u, **data):
    return UserSettings(user_id=u.id, data=data)


async def main_async():
    db_file = Path(tempfile.gettempdir()) / f"mindsync_mail_probe_{uuid.uuid4().hex[:6]}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    settings.smtp_host, settings.smtp_port, settings.smtp_starttls = "127.0.0.1", PORT, False
    settings.smtp_user, settings.smtp_password, settings.smtp_from = "", "", "mindsync@example.test"
    ctl, sink = start_sink()
    NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)

    async with Session() as db:
        # 1. default behaviour: one e-mail 48 hours before, once
        a = mk_user("alice")
        ta = mk_task(a, "Statistics report", NOW + timedelta(hours=40))
        db.add_all([a, ta, mk_set(a, remind_enabled=True)])
        await db.commit()
        r = await reminders.run_cycle(db, NOW, only_user=a.id)
        check("a task due in 40 h gets one e-mail through a real SMTP connection", r["emails"] == 1 and len(sink.messages) == 1 and r["mode"] == "smtp", str(r))
        to, msg = sink.messages[-1]
        check("it is addressed only to its owner and names the task", to == [a.email] and "Statistics report" in body_of(msg) and msg["To"] == a.email)
        log = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == a.id))).all()
        check("the log says 'sent' (accepted by the mail server), not 'delivered'", [l.status for l in log] == ["sent"] and "accepted" in log[0].detail, str([(l.status, l.detail) for l in log]))
        await reminders.run_cycle(db, NOW + timedelta(minutes=15), only_user=a.id)
        await reminders.run_cycle(db, NOW + timedelta(hours=3), only_user=a.id)
        check("running the job again does not send the same reminder twice", len(sink.messages) == 1)
        # 2. rescheduling: a new deadline re-arms
        ta.deadline = NOW + timedelta(hours=60)
        await db.commit()
        await reminders.run_cycle(db, NOW + timedelta(hours=14), only_user=a.id)       # deadline now 46 h away
        check("moving the deadline re-arms the reminder (a new e-mail for the new deadline)", len(sink.messages) == 2, str(len(sink.messages)))
        check("and the new e-mail shows the new deadline", "01 Nov" in body_of(sink.messages[-1][1]), body_of(sink.messages[-1][1])[:200].replace("\n", " | "))

        # 3. time zones: Auckland is already on the next calendar day
        n0 = len(sink.messages)
        b = mk_user("bea")
        # deadline 2026-10-30 18:00 in Auckland (NZDT, UTC+13) = 2026-10-30 05:00 UTC. At 2026-10-29 19:30 UTC it is 2026-10-30 08:30 in Auckland.
        tb = mk_task(b, "Presentation slides", datetime(2026, 10, 30, 5, 0, tzinfo=timezone.utc))
        db.add_all([b, tb, mk_set(b, remind_enabled=True, remind_lead_hours=[1], same_day_reminder=True, same_day_hour=8, timezone="Pacific/Auckland")])
        await db.commit()
        await reminders.run_cycle(db, datetime(2026, 10, 29, 18, 0, tzinfo=timezone.utc), only_user=b.id)    # 07:00 Auckland on the 30th
        check("same-day reminder is NOT sent before the student's chosen hour in their own time zone", len(sink.messages) == n0)
        await reminders.run_cycle(db, datetime(2026, 10, 29, 19, 30, tzinfo=timezone.utc), only_user=b.id)   # 08:30 Auckland
        check("same-day reminder arrives after the chosen hour, even though it is still the 29th in UTC", len(sink.messages) == n0 + 1)
        txt = body_of(sink.messages[-1][1])
        check("the time in the e-mail is the student's local time (18:00 in Auckland), not UTC", "18:00" in txt and "05:00" not in txt, txt.replace("\n", " | ")[:200])
        check("the subject says it is due today", "due today" in str(sink.messages[-1][1]["Subject"]), str(sink.messages[-1][1]["Subject"]))
        await reminders.run_cycle(db, datetime(2026, 10, 29, 22, 0, tzinfo=timezone.utc), only_user=b.id)
        check("the same-day reminder is sent once per day", len(sink.messages) == n0 + 1)

        # 4. overdue
        n0 = len(sink.messages)
        c = mk_user("cy")
        tc1, tc2 = mk_task(c, "Missed yesterday", NOW - timedelta(hours=5)), mk_task(c, "Missed long ago", NOW - timedelta(days=5))
        db.add_all([c, tc1, tc2, mk_set(c, remind_enabled=True, overdue_reminder=True, remind_lead_hours=[48])])
        await db.commit()
        await reminders.run_cycle(db, NOW, only_user=c.id)
        txt = body_of(sink.messages[-1][1]) if len(sink.messages) > n0 else ""
        check("overdue reminder is sent for a task 5 hours late, and not for one 5 days late", len(sink.messages) == n0 + 1 and "Missed yesterday" in txt and "Missed long ago" not in txt)

        # 5. several lead times already due -> one e-mail
        n0 = len(sink.messages)
        d = mk_user("dee")
        td = mk_task(d, "Short notice task", NOW + timedelta(hours=10))
        db.add_all([d, td, mk_set(d, remind_enabled=True, remind_lead_hours=[24, 48, 168])])
        await db.commit()
        await reminders.run_cycle(db, NOW, only_user=d.id)
        logs = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == d.id))).all()
        check("a task created 10 h before its deadline with three lead times sends ONE e-mail", len(sink.messages) == n0 + 1 and sorted(l.status for l in logs) == ["sent", "skipped", "skipped"], str(sorted(l.status for l in logs)))

        # 6. opt-outs and finished tasks
        n0 = len(sink.messages)
        e1, e2, e3 = mk_user("opt_out", alerts=False), mk_user("reminders_off"), mk_user("finished")
        db.add_all([e1, e2, e3, mk_task(e1, "x1", NOW + timedelta(hours=5)), mk_task(e2, "x2", NOW + timedelta(hours=5)),
                    mk_task(e3, "x3", NOW + timedelta(hours=5), TaskStatus.completed),
                    mk_set(e1, remind_enabled=True), mk_set(e2, remind_enabled=False), mk_set(e3, remind_enabled=True)])
        await db.commit()
        await reminders.run_cycle(db, NOW)
        got = [m[0][0] for m in sink.messages[n0:]]
        check("no e-mail for a student who switched alerts off, one whose reminders are off, or a finished task", not any(x.split("-")[0] in ("opt_out", "reminders_off", "finished") for x in got), str(got))

        # 7. hostile title
        n0 = len(sink.messages)
        h = mk_user("hank")
        evil = "Report\r\nBcc: attacker@evil.example\r\nSubject: hacked <script>alert(1)</script>"
        db.add_all([h, mk_task(h, evil, NOW + timedelta(hours=5)), mk_set(h, remind_enabled=True)])
        await db.commit()
        await reminders.run_cycle(db, NOW, only_user=h.id)
        m = sink.messages[-1][1]
        raw = m.as_string()
        check("a task title with line breaks cannot add e-mail headers or recipients", len(sink.messages) == n0 + 1 and m["Bcc"] is None and sink.messages[-1][0] == [h.email] and "hacked" not in str(m["Subject"]))
        html_part = m.get_body(("html",)).get_content()
        check("markup in a title is escaped in the HTML part", "<script>" not in html_part and "&lt;script&gt;" in html_part)

        # 8. failure: server down -> 'failed', no crash, retry only after 15 minutes, then success with attempts=2
        n0 = len(sink.messages)
        f = mk_user("finn")
        db.add_all([f, mk_task(f, "Retry me", NOW + timedelta(hours=5)), mk_set(f, remind_enabled=True)])
        await db.commit()
        ctl.stop()
        r = await reminders.run_cycle(db, NOW, only_user=f.id)
        fl = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == f.id))).all()
        check("mail server down: the cycle survives and records 'failed' with a short code (no server text, no secrets)",
              r["failures"] == 1 and [l.status for l in fl] == ["failed"] and fl[0].detail == "error: refused", str([(l.status, l.detail) for l in fl]))
        ctl, sink2 = start_sink()
        await reminders.run_cycle(db, NOW + timedelta(minutes=5), only_user=f.id)
        check("it does not hammer the server: no retry within 15 minutes", len(sink2.messages) == 0)
        await reminders.run_cycle(db, NOW + timedelta(minutes=16), only_user=f.id)
        fl = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == f.id))).all()
        check("after 15 minutes it retries, the e-mail arrives and the log shows sent with 2 attempts", len(sink2.messages) == 1 and fl[0].status == "sent" and fl[0].attempts == 2, str([(l.status, l.attempts) for l in fl]))
        sink = sink2

        # 9. refused login
        ctl.stop()
        ctl, sink3 = start_sink(auth=True)
        settings.smtp_user, settings.smtp_password = "someone", "wrong-password-xyz"
        g = mk_user("gus")
        db.add_all([g, mk_task(g, "Auth fail", NOW + timedelta(hours=5)), mk_set(g, remind_enabled=True)])
        await db.commit()
        r = await reminders.run_cycle(db, NOW, only_user=g.id)
        gl = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == g.id))).all()
        check("a refused mail login is recorded as 'failed: auth' and the password is not stored anywhere", r["failures"] == 1 and gl and gl[0].detail == "error: auth" and "wrong-password" not in str([(l.detail) for l in gl]), str([(l.status, l.detail) for l in gl]))
        code, hint = notifier.classify_mail_error(__import__("smtplib").SMTPAuthenticationError(535, b"secret text from server"))
        check("the hint shown to the student is a fixed sentence without the server's own text", code == "auth" and "secret text" not in hint)
        settings.smtp_user, settings.smtp_password = "", ""
        ctl.stop()

        # 10. practice mode (no mail server): honest status
        settings.smtp_host = ""
        n0 = len(sink3.messages)
        i = mk_user("ivy")
        db.add_all([i, mk_task(i, "Practice mode", NOW + timedelta(hours=5)), mk_set(i, remind_enabled=True)])
        await db.commit()
        notifier.OUTBOX_DIR = Path(tempfile.mkdtemp())
        r = await reminders.run_cycle(db, NOW, only_user=i.id)
        il = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == i.id))).all()
        check("with no mail server the reminder is saved as a file and logged 'outbox', never 'sent'", r["mode"] == "outbox" and [l.status for l in il] == ["outbox"] and len(list(notifier.OUTBOX_DIR.glob("*.eml"))) == 1, str(r))
    await engine.dispose()
    try:
        db_file.unlink(missing_ok=True)
    except OSError:
        pass


def main() -> int:
    asyncio.run(main_async())
    passed = sum(1 for _, ok in results if ok)
    out = Path(__file__).resolve().parents[2] / "docs" / "email_integration_results.md"
    lines = [f"### E-mail reminders against a local mail-collecting server, {datetime.now():%Y-%m-%d %H:%M}", "",
             f"**{passed} / {len(results)} checks passed.** Real smtplib code, real database, real reminder cycle; the mail server is a local receiver, so nothing was sent to the internet and live delivery by a real provider (for example Gmail) is NOT covered.", "",
             "| Check | Result |", "|---|---|"] + [f"| {n.replace('|', '/')} | {'PASS' if ok else 'FAIL'} |" for n, ok in results]
    out.parent.mkdir(exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n")
    print(f"\n{passed} / {len(results)} passed. Saved to docs/email_integration_results.md")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
