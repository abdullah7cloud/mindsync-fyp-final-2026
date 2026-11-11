"""Email deadline alerts: email content, 2-day window, send-once, opt-out, retry on failure, outbox mode."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import notifier
from app.config import settings
from app.database import Base
from app.models import Task, TaskStatus, User

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def _user(email="a@example.com", alerts=True):
    return User(id=uuid.uuid4(), email=email, password_hash="x", display_name="Abi", email_alerts=alerts)


def _task(owner, title, hours, status=TaskStatus.pending, sent=None):
    return Task(id=uuid.uuid4(), owner_id=owner.id, title=title, description="", category="general",
                difficulty=3, deadline=NOW + timedelta(hours=hours), status=status, reminder_sent_at=sent)


def run(coro):
    return asyncio.run(coro)


async def _seed_and_cycle(objs, sender, only_user=None):
    pytest.importorskip("aiosqlite")   # test-only dependency (in requirements.txt)
    from tests.dbutil import make_engine
    engine = await make_engine()
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        from tests.dbutil import seed
        await seed(db, objs)
        result = await notifier.run_reminder_cycle(db, now=NOW, only_user=only_user, sender=sender)
        await db.commit()
        # reload tasks
        from sqlalchemy import select
        tasks = list((await db.scalars(select(Task))).all())
    await engine.dispose()
    return result, tasks


def test_email_lists_tasks_and_escapes_html():
    u = _user()
    msg = notifier.build_reminder_email(u, [_task(u, "Essay <b>draft</b>", 30), _task(u, "Lab report", 5)], NOW)
    assert msg["To"] == "a@example.com"
    assert "2 tasks are due soon" in msg["Subject"]
    text = msg.get_body(("plain",)).get_content()
    html_part = msg.get_body(("html",)).get_content()
    assert "Lab report" in text and "Essay <b>draft</b>" in text
    assert "&lt;b&gt;draft&lt;/b&gt;" in html_part and "<b>draft</b>" not in html_part
    assert text.index("Lab report") < text.index("Essay")   # soonest first


def test_single_task_subject_and_header_injection_is_blocked():
    u = _user()
    msg = notifier.build_reminder_email(u, [_task(u, "Read\r\nBcc: evil@example.com", 10)], NOW)
    assert msg["Subject"] == "MindSync: 1 task is due soon"
    assert msg["Bcc"] is None


def test_only_tasks_inside_48_hours_are_alerted():
    u = _user()
    near, far, past, done = _task(u, "near", 40), _task(u, "far", 100), _task(u, "past", -3), _task(u, "done", 20, TaskStatus.completed)
    sent = []

    async def sender(msg):
        sent.append(msg)
        return "outbox"

    result, tasks = run(_seed_and_cycle([u, near, far, past, done], sender))
    assert result["emails"] == 1 and result["tasks"] == 1
    by = {t.title: t for t in tasks}
    assert by["near"].reminder_sent_at is not None
    assert all(by[n].reminder_sent_at is None for n in ("far", "past", "done"))


def test_one_email_per_user_and_each_task_only_once():
    u1, u2 = _user("one@example.com"), _user("two@example.com")
    objs = [u1, u2, _task(u1, "a", 10), _task(u1, "b", 20), _task(u2, "c", 30),
            _task(u2, "already", 12, sent=NOW - timedelta(hours=5))]
    sent = []

    async def sender(msg):
        sent.append(msg["To"])
        return "outbox"

    result, _ = run(_seed_and_cycle(objs, sender))
    assert sorted(sent) == ["one@example.com", "two@example.com"]
    assert result["tasks"] == 3


def test_users_who_opted_out_get_nothing():
    u = _user(alerts=False)
    sent = []

    async def sender(msg):
        sent.append(msg)
        return "outbox"

    result, _ = run(_seed_and_cycle([u, _task(u, "x", 10)], sender))
    assert result["emails"] == 0 and sent == []


def test_failed_send_is_retried_next_time():
    u = _user()

    async def broken(msg):
        raise OSError("mail server down")

    result, tasks = run(_seed_and_cycle([u, _task(u, "x", 10)], broken))
    assert result["failures"] == 1 and result["emails"] == 0
    assert tasks[0].reminder_sent_at is None


def test_check_now_only_touches_the_requesting_user():
    u1, u2 = _user("one@example.com"), _user("two@example.com")
    sent = []

    async def sender(msg):
        sent.append(msg["To"])
        return "outbox"

    result, _ = run(_seed_and_cycle([u1, u2, _task(u1, "a", 10), _task(u2, "b", 10)], sender, only_user=u1.id))
    assert sent == ["one@example.com"] and result["tasks"] == 1


def test_outbox_mode_writes_an_eml_file_when_no_smtp(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(notifier, "OUTBOX_DIR", tmp_path)
    u = _user()
    mode = run(notifier.deliver(notifier.build_test_email(u)))
    assert mode == "outbox"
    files = list(tmp_path.glob("*.eml"))
    assert len(files) == 1 and b"test email" in files[0].read_bytes().lower()
    assert notifier.delivery_mode() == "outbox"


def test_naive_deadlines_from_the_database_are_treated_as_utc():
    u = _user()
    t = _task(u, "naive", 10)
    t.deadline = t.deadline.replace(tzinfo=None)
    msg = notifier.build_reminder_email(u, [t], NOW)
    assert "naive" in msg.get_body(("plain",)).get_content()


# ---------- real-email safety: encryption before login, no secrets in messages, plain-English errors ----------
import smtplib
import socket
import ssl


class _FakeSMTP:
    """Stands in for smtplib.SMTP so no network is used; remembers the order of calls."""
    calls: list = []

    def __init__(self, host, port, timeout=None, context=None):
        _FakeSMTP.calls = [("connect", host, port)]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        assert context is not None            # certificate checking must be on
        _FakeSMTP.calls.append(("starttls",))

    def login(self, user, password):
        _FakeSMTP.calls.append(("login", user, password))

    def send_message(self, msg):
        _FakeSMTP.calls.append(("send",))

    def noop(self):
        _FakeSMTP.calls.append(("noop",))


def _smtp_settings(monkeypatch, **kw):
    base = dict(smtp_host="smtp.example.com", smtp_port=587, smtp_user="me@example.com",
                smtp_password="secret-pass", smtp_from="", smtp_starttls=True)
    base.update(kw)
    for k, v in base.items():
        monkeypatch.setattr(settings, k, v)


def test_starttls_happens_before_the_password_is_sent(monkeypatch):
    _smtp_settings(monkeypatch)
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    notifier._send_smtp_blocking(notifier.build_test_email(_user()))
    order = [c[0] for c in _FakeSMTP.calls]
    assert order == ["connect", "starttls", "login", "send"]


def test_login_without_encryption_is_refused(monkeypatch):
    _smtp_settings(monkeypatch, smtp_starttls=False)
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    _FakeSMTP.calls = []     # forget calls from earlier tests
    with pytest.raises(notifier.MailConfigError):
        notifier._send_smtp_blocking(notifier.build_test_email(_user()))
    assert ("login", "me@example.com", "secret-pass") not in _FakeSMTP.calls   # the password was never sent
    assert any("unencrypted" in p for p in notifier.config_problems())


def test_gmail_app_password_spaces_are_removed(monkeypatch):
    _smtp_settings(monkeypatch, smtp_host="smtp.gmail.com", smtp_user="me@gmail.com", smtp_password="abcd efgh ijkl mnop")
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    notifier.check_connection()
    assert ("login", "me@gmail.com", "abcdefghijklmnop") in _FakeSMTP.calls


def test_config_problems_are_plain_english_and_never_contain_the_password(monkeypatch):
    _smtp_settings(monkeypatch, smtp_password="", smtp_user="me@example.com")
    problems = notifier.config_problems()
    assert any("SMTP_PASSWORD is empty" in p for p in problems)
    _smtp_settings(monkeypatch, smtp_password="TopSecret123", smtp_starttls=False, smtp_from="x")
    assert "TopSecret123" not in " ".join(notifier.config_problems())
    monkeypatch.setattr(settings, "smtp_host", "")
    assert notifier.config_problems() == []          # demo mode is not a problem


@pytest.mark.parametrize("exc,code", [
    (smtplib.SMTPAuthenticationError(535, b"bad credentials for me@example.com"), "auth"),
    (smtplib.SMTPSenderRefused(550, b"no", "a@b.c"), "sender"),
    (smtplib.SMTPRecipientsRefused({}), "recipient"),
    (ssl.SSLCertVerificationError("certificate verify failed"), "tls"),
    (socket.gaierror(-2, "Name or service not known"), "dns"),
    (TimeoutError("timed out"), "timeout"),
    (ConnectionRefusedError(), "refused"),
    (notifier.MailConfigError("x"), "config"),
    (RuntimeError("boom"), "other"),
])
def test_mail_errors_become_fixed_plain_hints(exc, code):
    got_code, hint = notifier.classify_mail_error(exc)
    assert got_code == code
    assert "bad credentials" not in hint and "me@example.com" not in hint   # raw error text is never echoed


def test_failed_alert_logs_a_code_not_the_error_text(monkeypatch, caplog):
    async def boom(msg):
        raise smtplib.SMTPAuthenticationError(535, b"password=hunter2 rejected")
    u = _user()
    with caplog.at_level("WARNING", logger="mindsync.notifier"):
        result, _ = run(_seed_and_cycle([u, _task(u, "Essay", 10)], boom))
    assert result["failures"] == 1
    assert "hunter2" not in caplog.text and "auth" in caplog.text
