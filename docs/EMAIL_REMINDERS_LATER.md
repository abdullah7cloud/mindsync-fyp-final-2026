# Email reminders: how to switch them on later (not active today)

**Today: no email is ever sent.** Daily and deadline reminders appear **inside MindSync** only (the bell, and the Reminders box on My Tasks). The page says so in plain words, and Settings shows the email option as "not available in this version". This is true and tested; it is not a hidden feature.

## What already exists

* `backend/app/notifier.py` can send mail through SMTP (tested with a fake mail server, never with a real one in this version). With `SMTP_HOST` empty it saves the message as an `.eml` file in `backend/outbox` instead of sending it.
* The older "deadline in 48 hours" email alert (`docs/EMAIL_ALERTS.md`) uses that code. It is **off by default** until a mail server is set in `backend/.env`.
* The new in-app reminders are stored in the `notifications` table. A student's wish for email is stored as the setting `email_reminders_future` only; nothing reads it yet.

## To add email reminders later (a small piece of new work)

1. Choose a mail service (a Gmail App password works for a demonstration: `docs/EMAIL_ALERTS.md`).
2. Put `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` only in `backend/.env`, and test with `test-email.bat`.
3. Write a small job that, for each new row in `notifications` whose student has `email_reminders_future` on, calls the existing `deliver_quietly()` once and records that it was sent (so there is never a second email for the same reminder; the unique key `daily:<date>` / `deadline:<task>:<lead>` already prevents duplicates in the table).
4. Ask the student to confirm their email address first (a confirmation link). That is why changing the sign-in email in this version is protected by the password but sends no confirmation mail.
5. Turn the Settings email control on and remove the "not available" note. Add tests with a fake SMTP server before using a real one.

Do not tell anyone email works until you have sent and received a real test message.
