"""
Email deadline alerts.

A small background job (started with the API) checks every few minutes for
pending tasks whose deadline is within `reminder_hours_before` hours (48 by
default = "2 days before") and emails the owner ONE message listing them.
Each task is alerted only once (tasks.reminder_sent_at); changing a task's
deadline re-arms its alert.

Works with or without a mail server:
  * SMTP_HOST set  -> the email is really sent (e.g. Gmail app password, Brevo, Mailtrap). Passwords come only
    from backend/.env (never from code), the connection is encrypted before login, and errors are logged
    without any secret text.
  * SMTP_HOST blank -> the email is written to backend/outbox/*.eml so the feature can
    still be demonstrated and tested fully offline. The dashboard says which mode is active.

Safety notes: only the owner's own task titles go into the email, the HTML part is
escaped, and EmailMessage rejects header injection (no user text is placed in headers
except the recipient address, which was validated as an e-mail at sign-up).
"""
import asyncio
import html
import logging
import re
import smtplib
import socket
import ssl
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Task, TaskStatus, User

log = logging.getLogger("mindsync.notifier")

OUTBOX_DIR = Path(__file__).resolve().parent.parent / "outbox"


def smtp_configured() -> bool:
    return bool(settings.smtp_host.strip())


def delivery_mode() -> str:
    return "smtp" if smtp_configured() else "outbox"


def _sender() -> str:
    return settings.smtp_from.strip() or settings.smtp_user.strip() or "mindsync@localhost"


class MailConfigError(Exception):
    """The mail settings are unsafe or incomplete (raised BEFORE any password is sent anywhere)."""


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _is_local(host: str) -> bool:
    return host.strip().lower() in _LOCAL_HOSTS


def _smtp_password() -> str:
    """Google shows app passwords as 'abcd efgh ijkl mnop'. The spaces are only for reading, so drop them for Gmail."""
    pw = settings.smtp_password
    if settings.smtp_host.strip().lower().endswith("gmail.com"):
        pw = pw.replace(" ", "")
    return pw


def config_problems() -> list[str]:
    """
    Plain-English problems with the mail settings. Never contains a password or any secret value,
    so it is safe to print or log. Empty list = nothing obviously wrong.
    """
    if not smtp_configured():
        return []
    host = settings.smtp_host.strip().lower()
    user, pw = settings.smtp_user.strip(), settings.smtp_password
    problems = []
    if user and not pw:
        problems.append("SMTP_USER is set but SMTP_PASSWORD is empty.")
    if pw and not user:
        problems.append("SMTP_PASSWORD is set but SMTP_USER is empty.")
    if not user and not _is_local(host):
        problems.append("Most mail providers need both SMTP_USER and SMTP_PASSWORD.")
    if user and not _is_local(host) and settings.smtp_port != 465 and not settings.smtp_starttls:
        problems.append("Login over an unencrypted connection is refused. Use SMTP_PORT=587 with SMTP_STARTTLS=true, or SMTP_PORT=465.")
    if host.endswith("gmail.com") and settings.smtp_from.strip() and user and settings.smtp_from.strip().lower() != user.lower():
        problems.append("Gmail only sends from your own address: set SMTP_FROM to the same address as SMTP_USER (or leave it blank).")
    if "@" not in _sender():
        problems.append("SMTP_FROM (or SMTP_USER) should be a full email address.")
    return problems


def classify_mail_error(exc: BaseException) -> tuple[str, str]:
    """
    Turn an SMTP/network exception into (short code, plain-English hint).
    The hint is a FIXED sentence: the raw exception text is never shown to the user or logged,
    because it can echo server banners or account names.
    """
    if isinstance(exc, MailConfigError):
        return "config", "The mail settings in backend/.env are incomplete or unsafe. Run test-email.bat for details."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "auth", ("The mail server refused the username or password. For Gmail use a 16-letter App password "
                        "(not your normal password) and make sure 2-Step Verification is on.")
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "sender", "The mail server refused the From address. Set SMTP_FROM to an address your provider allows (usually the same as SMTP_USER)."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "recipient", "The mail server refused the recipient address."
    if isinstance(exc, smtplib.SMTPNotSupportedError):
        return "tls", "The mail server does not support the encryption setting chosen. Try SMTP_PORT=587 with SMTP_STARTTLS=true, or SMTP_PORT=465."
    if isinstance(exc, ssl.SSLError):
        return "tls", "The secure connection to the mail server failed. Check SMTP_PORT (587 with STARTTLS, or 465) and that your clock is correct."
    if isinstance(exc, socket.gaierror):
        return "dns", "The mail server name could not be found. Check SMTP_HOST and your internet connection."
    if isinstance(exc, (TimeoutError, socket.timeout, smtplib.SMTPServerDisconnected)):
        return "timeout", "The mail server did not answer in time. Check SMTP_PORT, your internet and any firewall or antivirus blocking outgoing mail."
    if isinstance(exc, ConnectionRefusedError):
        return "refused", "The mail server refused the connection. Check SMTP_HOST and SMTP_PORT."
    if isinstance(exc, OSError):
        return "network", "Could not reach the mail server. Check your internet connection, SMTP_HOST and SMTP_PORT."
    return "other", "The mail server did not accept the email. Run test-email.bat for details."


# ---------- building the email (pure, easy to test) ----------
def _aware(dt: datetime) -> datetime:
    """Treat a timezone-less datetime as UTC (some databases drop the zone)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _when_text(deadline: datetime, now: datetime) -> str:
    deadline = _aware(deadline)
    hours = (deadline - now).total_seconds() / 3600
    if hours < 1:
        return "in less than an hour"
    if hours < 24:
        return f"in about {round(hours)} hour{'s' if round(hours) != 1 else ''}"
    days = hours / 24
    return f"in about {days:.1f} days" if days < 2.5 else f"in {round(days)} days"


def _local_text(dt: datetime, tz_name: str) -> str:
    from zoneinfo import ZoneInfo
    local = _aware(dt).astimezone(ZoneInfo(tz_name))
    return local.strftime("%a %d %b %Y, %H:%M ") + (tz_name if tz_name != "UTC" else "UTC")


def build_digest_email(user: User, groups: dict, now: Optional[datetime] = None, tz_name: str = "UTC") -> EmailMessage:
    """One e-mail for everything that is due for this student right now: due soon, due today, overdue. Times are in THEIR time zone."""
    now = now or datetime.now(timezone.utc)
    present = {k: sorted(v, key=lambda t: _aware(t.deadline)) for k, v in groups.items() if v}
    titles = {"lead": "Due soon", "same_day": "Due today", "overdue": "Overdue"}
    total = sum(len(v) for v in present.values())
    if len(present) == 1:
        kind = next(iter(present))
        word = {"lead": "due soon", "same_day": "due today", "overdue": "overdue"}[kind]
        subject = f"MindSync: 1 task is {word}" if total == 1 else f"MindSync: {total} tasks are {word}"
    else:
        subject = f"MindSync: {total} tasks need your attention"
    name = (user.display_name or "there").strip()[:60] or "there"
    txt, htm = [f"Hi {name},\n"], [f"<p>Hi {html.escape(name)},</p>"]
    for kind in ("overdue", "same_day", "lead"):
        if kind not in present:
            continue
        txt.append(f"\n{titles[kind]}:")
        items = []
        for t in present[kind]:
            title = re.sub(r"\s+", " ", t.title).strip()[:120]
            when = _local_text(t.deadline, tz_name)
            txt.append(f"  - {title}  (due {when})")
            items.append(f"<li><strong>{html.escape(title)}</strong> - due {html.escape(when)}</li>")
        htm.append(f"<h3>{titles[kind]}</h3><ul>{''.join(items)}</ul>")
    txt.append(f"\nOpen MindSync to see your plan: {settings.app_url}\n\nYou can change when you get these, or switch them off, in Settings.\n")
    htm.append(f"<p><a href=\"{html.escape(settings.app_url)}\">Open MindSync</a> to see your plan.</p>"
               "<p style=\"color:#666;font-size:12px\">You can change when you get these, or switch them off, in Settings.</p>")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _sender()
    msg["To"] = user.email
    msg.set_content("\n".join(txt))
    msg.add_alternative("".join(htm), subtype="html")
    return msg


def build_reminder_email(user: User, tasks: list[Task], now: Optional[datetime] = None) -> EmailMessage:
    now = now or datetime.now(timezone.utc)
    tasks = sorted(tasks, key=lambda t: _aware(t.deadline))
    n = len(tasks)
    name = (user.display_name or "there").strip()[:60] or "there"

    lines_txt, lines_html = [], []
    for t in tasks:
        title = re.sub(r"\s+", " ", t.title).strip()[:120]
        due = _aware(t.deadline).astimezone(timezone.utc).strftime("%a %d %b %Y, %H:%M UTC")
        lines_txt.append(f"  - {title}  (due {due}, {_when_text(t.deadline, now)})")
        lines_html.append(
            f"<li><strong>{html.escape(title)}</strong> - due {html.escape(due)} "
            f"<em>({html.escape(_when_text(t.deadline, now))})</em></li>"
        )

    subject = (
        "MindSync: 1 task is due soon" if n == 1 else f"MindSync: {n} tasks are due soon"
    )
    body_txt = (
        f"Hi {name},\n\n"
        f"This is your MindSync deadline alert. {'This task is' if n == 1 else 'These tasks are'} "
        f"due within the next {settings.reminder_hours_before // 24 or 1} day(s):\n\n"
        + "\n".join(lines_txt)
        + f"\n\nOpen MindSync to see what to work on first: {settings.app_url}\n\n"
        "You can switch these alerts off any time on your dashboard.\n"
    )
    body_html = (
        f"<p>Hi {html.escape(name)},</p>"
        f"<p>This is your MindSync deadline alert. {'This task is' if n == 1 else 'These tasks are'} "
        f"due soon:</p><ul>{''.join(lines_html)}</ul>"
        f"<p><a href=\"{html.escape(settings.app_url)}\">Open MindSync</a> to see what to work on first.</p>"
        "<p style=\"color:#666;font-size:12px\">You can switch these alerts off any time on your dashboard.</p>"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _sender()
    msg["To"] = user.email
    msg.set_content(body_txt)
    msg.add_alternative(body_html, subtype="html")
    return msg


def build_test_email(user: User) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "MindSync: test email"
    msg["From"] = _sender()
    msg["To"] = user.email
    msg.set_content(
        f"Hi {user.display_name},\n\nThis is a test email from MindSync. "
        "If you can read it, deadline alerts will reach you.\n"
    )
    return msg


def build_reset_email(user: User, link: str, minutes: int) -> EmailMessage:
    """The "forgot password" message. The link is the only secret in it; it is never logged."""
    msg = EmailMessage()
    msg["Subject"] = "MindSync: reset your password"
    msg["From"] = _sender()
    msg["To"] = user.email
    name = user.display_name
    msg.set_content(
        f"Hi {name},\n\n"
        "Someone (hopefully you) asked to reset the password of your MindSync account.\n"
        f"Open this link within {minutes} minutes to choose a new password:\n\n{link}\n\n"
        "The link works once. If you did not ask for this, you can ignore this email: your password stays as it is.\n"
    )
    msg.add_alternative(
        f"<p>Hi {html.escape(name)},</p>"
        "<p>Someone (hopefully you) asked to reset the password of your MindSync account.</p>"
        f"<p><a href=\"{html.escape(link)}\">Choose a new password</a> (the link works once and expires in {minutes} minutes).</p>"
        "<p>If you did not ask for this, ignore this email: your password stays as it is.</p>",
        subtype="html",
    )
    return msg


def build_password_changed_email(user: User) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "MindSync: your password was changed"
    msg["From"] = _sender()
    msg["To"] = user.email
    msg.set_content(
        f"Hi {user.display_name},\n\nThe password of your MindSync account was just changed. "
        "If this was you, no action is needed. If it was not, use \"Forgot password?\" on the login page "
        "straight away to set a new one.\n"
    )
    return msg


# ---------- delivering the email ----------
@contextmanager
def _smtp_session():
    """
    Open a SECURE connection to the mail server and log in. Port 465 = encrypted from the start,
    otherwise STARTTLS upgrades the connection BEFORE the password is sent. If a login is needed
    but no encryption is configured, we refuse rather than send the password in clear text.
    """
    host, port = settings.smtp_host.strip(), settings.smtp_port
    user = settings.smtp_user.strip()
    if user and not _is_local(host) and port != 465 and not settings.smtp_starttls:
        raise MailConfigError("login without encryption refused")
    ctx = ssl.create_default_context()      # verifies the server's certificate
    server = smtplib.SMTP_SSL(host, port, timeout=15, context=ctx) if port == 465 else smtplib.SMTP(host, port, timeout=15)
    with server as s:
        if port != 465 and settings.smtp_starttls:
            s.starttls(context=ctx)
        if user:
            s.login(user, _smtp_password())
        yield s


def _send_smtp_blocking(msg: EmailMessage) -> None:
    with _smtp_session() as s:
        s.send_message(msg)


def check_connection() -> None:
    """Connect and log in WITHOUT sending anything (used by test-email.bat). Raises on any problem."""
    with _smtp_session() as s:
        s.noop()


def _write_outbox(msg: EmailMessage) -> Path:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = OUTBOX_DIR / f"{stamp}-{uuid.uuid4().hex[:6]}.eml"
    path.write_bytes(bytes(msg))
    return path


async def deliver(msg: EmailMessage) -> str:
    """Send (or save) one email. Returns 'smtp' or 'outbox'. Raises on SMTP failure."""
    if smtp_configured():
        await asyncio.to_thread(_send_smtp_blocking, msg)
        return "smtp"
    await asyncio.to_thread(_write_outbox, msg)
    return "outbox"


# ---------- the reminder cycle ----------
async def find_due_tasks(db: AsyncSession, now: datetime, only_user: Optional[uuid.UUID] = None) -> dict[uuid.UUID, tuple[User, list[Task]]]:
    """Version 1 helper kept for compatibility: pending, not-yet-alerted tasks inside the default window, grouped by owner."""
    horizon = now + timedelta(hours=settings.reminder_hours_before)
    q = (
        select(Task, User)
        .join(User, User.id == Task.owner_id)
        .where(Task.status == TaskStatus.pending, Task.reminder_sent_at.is_(None), Task.deadline > now, Task.deadline <= horizon,
               User.email_alerts.is_(True))
    )
    if only_user is not None:
        q = q.where(User.id == only_user)
    grouped: dict[uuid.UUID, tuple[User, list[Task]]] = {}
    for task, user in (await db.execute(q)).all():
        grouped.setdefault(user.id, (user, []))[1].append(task)
    return grouped


async def run_reminder_cycle(db: AsyncSession, now: Optional[datetime] = None, only_user: Optional[uuid.UUID] = None,
                             sender: Callable = deliver) -> dict:
    """One pass of the reminder job (see app/reminders.py for the rules). A failed send is retried on later passes."""
    from app import reminders
    return await reminders.run_cycle(db, now=now, only_user=only_user, sender=sender)


async def reminder_loop(session_factory) -> None:
    """Background loop started by the API at start-up."""
    interval = max(1, settings.reminder_check_minutes) * 60
    await asyncio.sleep(5)  # let the API finish starting
    while True:
        try:
            async with session_factory() as db:
                result = await run_reminder_cycle(db)
                if result["emails"] or result["failures"]:
                    log.info("Reminder cycle: %s", result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("Reminder cycle failed: %s", type(exc).__name__)
        await asyncio.sleep(interval)


async def deliver_quietly(msg: EmailMessage, purpose: str) -> None:
    """
    Send one email without ever raising (used for background sending after the HTTP answer was already given).
    A failure is logged as a short error code only: never the address, the link or the exception text.
    """
    try:
        await deliver(msg)
    except Exception as exc:  # noqa: BLE001 - background job: must not crash the server
        code, _hint = classify_mail_error(exc)
        log.warning("Could not send %s email: %s (%s)", purpose, code, type(exc).__name__)
