"""
Checks your email settings WITHOUT printing any secret.

    python -m scripts.check_email                 # shows the settings (password hidden) and tries to log in
    python -m scripts.check_email --to me@x.com   # also sends one real test email to that address

It reads the same backend/.env the API uses (through app.config). Nothing is sent unless you pass --to.
The password is never printed, not even partly; only whether it is set and how many characters it has.
"""
import argparse
import sys

from app import notifier
from app.config import settings


def main() -> int:
    ap = argparse.ArgumentParser(description="Check MindSync email settings.")
    ap.add_argument("--to", help="send one real test email to this address")
    args = ap.parse_args()

    print("MindSync email check\n")
    user = settings.smtp_user.strip()
    masked_user = (user[:2] + "***" + user[user.find("@"):]) if "@" in user else ("(not set)" if not user else user[:2] + "***")
    print(f"  SMTP_HOST      : {settings.smtp_host.strip() or '(not set)'}")
    print(f"  SMTP_PORT      : {settings.smtp_port}")
    print(f"  SMTP_STARTTLS  : {settings.smtp_starttls}")
    print(f"  SMTP_USER      : {masked_user}")
    print(f"  SMTP_PASSWORD  : {'set (' + str(len(settings.smtp_password)) + ' characters, hidden)' if settings.smtp_password else '(not set)'}")
    print(f"  SMTP_FROM      : {settings.smtp_from.strip() or '(blank: SMTP_USER is used)'}")
    print()

    if not notifier.smtp_configured():
        print("RESULT: no mail server is set up (SMTP_HOST is blank), so emails are saved in backend/outbox.")
        print("        Run edit-email-settings.bat and follow docs/EMAIL_ALERTS.md.")
        return 1

    problems = notifier.config_problems()
    for p in problems:
        print(f"  PROBLEM: {p}")
    if problems:
        print("\nRESULT: fix the problems above in backend/.env, then run this check again.")
        return 1

    try:
        notifier.check_connection()
    except Exception as exc:
        code, hint = notifier.classify_mail_error(exc)
        print(f"RESULT: login FAILED ({code}).\n        {hint}")
        return 1
    print("  Connected securely and logged in: OK")

    if args.to:
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = "MindSync: test email"
        msg["From"] = notifier._sender()
        msg["To"] = args.to
        msg.set_content("This is a test email from MindSync. If you can read it, deadline alerts will reach you.\n")
        try:
            notifier._send_smtp_blocking(msg)
        except Exception as exc:
            code, hint = notifier.classify_mail_error(exc)
            print(f"RESULT: sending FAILED ({code}).\n        {hint}")
            return 1
        print(f"  Test email sent to {args.to}: OK (check the inbox and the spam folder)")
    else:
        print("  (Nothing was sent. Run test-email.bat and type an address to send a real test email.)")
    print("\nRESULT: email settings work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
