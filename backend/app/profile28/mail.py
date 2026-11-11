"""The e-mails of Update 28. Plain, friendly text plus a simple HTML copy. Student text is always escaped; no user text goes into a header."""
import html
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from app.notifier import _sender


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def remaining_text(deadline: datetime, now: datetime) -> str:
    """'3 days left', '5 hours left' ... in plain words."""
    secs = max(0, (_aware(deadline) - _aware(now)).total_seconds())
    if secs < 3600:
        return "less than an hour left"
    hours = secs / 3600
    if hours < 48:
        h = round(hours)
        return f"about {h} hour{'s' if h != 1 else ''} left"
    d = round(hours / 24)
    return f"about {d} days left"


def deadline_text(deadline: datetime, tz_name: str) -> str:
    local = _aware(deadline).astimezone(ZoneInfo(tz_name))
    return local.strftime("%A %d %B %Y, %H:%M")


def _name(display_name: str) -> str:
    return (display_name or "there").strip() or "there"


def build_task_reminder(to_email: str, display_name: str, items: list, tz_name: str, percent: int, now: datetime) -> EmailMessage:
    """items = [(title, deadline_utc), ...]. One friendly e-mail, one line per task."""
    items = sorted(items, key=lambda x: x[1])
    one = len(items) == 1
    msg = EmailMessage()
    msg["Subject"] = (f"MindSync: \"{items[0][0][:60]}\" is coming up" if one else f"MindSync: {len(items)} study tasks are coming up").replace("\n", " ")
    msg["From"] = _sender()
    msg["To"] = to_email
    lines = [f"- {t} - due {deadline_text(d, tz_name)} ({remaining_text(d, now)})" for t, d in items]
    text = (f"Hi {_name(display_name)},\n\n"
            f"A friendly nudge: you have about {percent}% of your time left for {'this task' if one else 'these tasks'}.\n\n"
            + "\n".join(lines) +
            f"\n\nTimes are shown in your time zone ({tz_name}).\n"
            "A little progress today keeps the pressure away. You can do this.\n\n"
            "You get this e-mail once per task. You can switch reminders off any time in MindSync > Settings.\n")
    rows = "".join(f"<li><strong>{html.escape(t)}</strong><br>Due {html.escape(deadline_text(d, tz_name))} &middot; {html.escape(remaining_text(d, now))}</li>" for t, d in items)
    msg.set_content(text)
    msg.add_alternative(
        f"<p>Hi {html.escape(_name(display_name))},</p>"
        f"<p>A friendly nudge: you have about {percent}% of your time left for {'this task' if one else 'these tasks'}.</p>"
        f"<ul>{rows}</ul><p>Times are shown in your time zone ({html.escape(tz_name)}).<br>A little progress today keeps the pressure away. You can do this.</p>"
        "<p style=\"color:#667\">You get this e-mail once per task. You can switch reminders off any time in MindSync &gt; Settings.</p>",
        subtype="html")
    return msg


def build_reminder_test(to_email: str, display_name: str, percent: int, tz_name: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "MindSync: your reminder test e-mail"
    msg["From"] = _sender()
    msg["To"] = to_email
    msg.set_content(f"Hi {_name(display_name)},\n\nThis is a test. If you can read it, MindSync can reach you.\n"
                    f"When a task has {percent}% of its time left, you will get an e-mail like this one (your time zone: {tz_name}).\n")
    return msg


def build_email_code(to_email: str, display_name: str, code: str, minutes: int) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "MindSync: your confirmation code"
    msg["From"] = _sender()
    msg["To"] = to_email
    msg.set_content(f"Hi {_name(display_name)},\n\nYour MindSync confirmation code is: {code}\n\n"
                    f"Type it in My Profile within {minutes} minutes to make this your new sign-in e-mail.\n"
                    "If you did not ask for this, ignore this e-mail: nothing changes.\n")
    msg.add_alternative(f"<p>Hi {html.escape(_name(display_name))},</p><p>Your MindSync confirmation code is:</p>"
                        f"<p style=\"font-size:24px;letter-spacing:4px\"><strong>{html.escape(code)}</strong></p>"
                        f"<p>Type it in My Profile within {minutes} minutes to make this your new sign-in e-mail.</p>"
                        "<p>If you did not ask for this, ignore this e-mail: nothing changes.</p>", subtype="html")
    return msg


def build_email_changed_notice(old_email: str, display_name: str, new_email: str) -> EmailMessage:
    """Sent to the OLD address, so a stolen login cannot move the account away silently."""
    msg = EmailMessage()
    msg["Subject"] = "MindSync: your sign-in e-mail was changed"
    msg["From"] = _sender()
    msg["To"] = old_email
    a, b = new_email.split("@", 1)
    hint = (a[:1] + "***@" + b) if a else "***@" + b
    msg.set_content(f"Hi {_name(display_name)},\n\nThe sign-in e-mail of your MindSync account was just changed to {hint}.\n"
                    "If this was you, no action is needed. If it was not, sign in with the new address if you can and change your password, "
                    "or use \"Forgot password?\" on the login page.\n")
    return msg
