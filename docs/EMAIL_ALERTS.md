# Email deadline alerts

MindSync emails a student **once** when a pending task is due within **2 days** (48 hours).

## How it works
1. When the backend starts it launches a small background job (`app/notifier.py`).
2. Every 15 minutes it looks for tasks that are `pending`, due within 48 hours, not overdue, not yet alerted, and owned by a user who has alerts switched on.
3. It sends **one email per student** listing those tasks (soonest first), then stamps each task with `reminder_sent_at` so it is never emailed twice.
4. If a student changes a task's deadline (or re-opens it), the stamp is cleared and the alert can fire again.
5. If the email cannot be sent (server down, wrong password) the tasks stay un-stamped and the next cycle retries.

## Dashboard controls ("Email deadline alerts" card)
- **On / Off switch**: opt out any time (stored as `users.email_alerts`).
- **Send test email**: sends a test message to your own address.
- **Check deadlines now**: runs the check for your account immediately (handy for a demo).

## Two modes
| Mode | When | What happens |
|---|---|---|
| Real email | `SMTP_HOST` is set in `backend/.env` | Message goes through your mail provider |
| Demo / outbox | `SMTP_HOST` is blank | Message is saved as a `.eml` file in `backend/outbox/` (double-click to open in any mail app) |

The dashboard tells the student which mode is active.

## Why you may see "No mail server is set up ... saved in backend/outbox"
`SMTP_HOST` is missing from `backend/.env`, so MindSync is in demo mode on purpose: nothing is lost, each email is saved as a `.eml` file in `backend/outbox/`. Real email needs an email account that lets MindSync log in. That login is **yours**, so you type it into `backend/.env` yourself (double-click `edit-email-settings.bat`); the assistant and the code never contain it.

## Choosing a provider (all work through the same five settings)
| Option | Cost | Good for | Notes |
|---|---|---|---|
| **Gmail + App password** (recommended to start) | Free | Sending alerts to yourself and a few testers | Needs 2-Step Verification. Gmail only sends "from" your own address. Personal accounts have daily sending limits, which is fine for a university project. |
| **Brevo** (SMTP relay) | Free tier (daily limit: check their site) | Sending to many students from a project address | Create a free account, then SMTP & API -> create an **SMTP key**. Use `smtp-relay.brevo.com`, port 587. The sender address must be verified in Brevo. |
| **Mailtrap Email Sandbox** | Free tier | Demo/testing: catches emails in a web inbox, never reaches real people | Good for a viva demo because nothing can be sent to the wrong person. |

## Switching on real email (Gmail example)
1. In your Google account turn on 2-Step Verification, then create an **App password** (Security -> App passwords). It is shown as `abcd efgh ijkl mnop`; MindSync accepts it with or without the spaces.
2. Double-click `edit-email-settings.bat` (opens `backend/.env` in Notepad) and add:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=youraddress@gmail.com
SMTP_PASSWORD=the-16-letter-app-password
SMTP_FROM=youraddress@gmail.com
SMTP_STARTTLS=true
```
3. Double-click `test-email.bat`. It shows your settings with the password hidden, tries a secure login, and (if you type an address) sends one real test email. It tells you in plain English what is wrong if it fails.
4. Run `restart-backend.bat`, then press **Send test email** on the dashboard. The card should say real email is on.

Never put the app password in the report, in GitHub, in a screenshot or in a chat. `backend/.env` is already in `.gitignore`. If you ever pasted it somewhere by mistake, delete that App password in your Google account and create a new one.

## Troubleshooting (what each message means)
| Message | Fix |
|---|---|
| "refused the username or password" | Use an App password, not your normal password; check 2-Step Verification is on; check `SMTP_USER`. |
| "refused the From address" | Set `SMTP_FROM` to the same address as `SMTP_USER` (Brevo: a verified sender). |
| "mail server name could not be found" | Typo in `SMTP_HOST`, or no internet. |
| "did not answer in time" | Wrong `SMTP_PORT`, or a firewall/antivirus blocks outgoing mail. Try 587 (STARTTLS) or 465. |
| "secure connection ... failed" | Port/encryption mismatch: 587 + `SMTP_STARTTLS=true`, or 465. Check the PC clock is right. |
| Email arrives but in spam | Normal for a new sender. Mark "not spam". |

## Other emails MindSync sends (added Oct 2026)
- **Password reset link** ("Forgot password?" on the login page): a one-time link valid for 30 minutes. In demo mode (no mail server) the message is saved in `backend/outbox` and the page says so; open the newest `.eml` file in Notepad or Outlook and click the link.
- **"Your password was changed"** notice after a reset or a change in the account panel.
Both use the same delivery code as the deadline alerts, so once real SMTP is configured they arrive in the real inbox. If sending fails, the answer on the page is unchanged and the log gets a short error code only (the link is never logged).

## Security design (for the report)
- Credentials are read from `backend/.env` only (never in code, never in the frontend, never returned by any endpoint, never logged).
- The connection is encrypted **before** the password is sent (STARTTLS on 587, or SSL on 465) and the server certificate is verified. If a login is configured but encryption is off, MindSync refuses to send the password (`MailConfigError`).
- Errors shown to the user and written to the log are fixed plain sentences plus a short code (for example `auth`, `dns`, `timeout`). The raw exception text is never shown or logged because it can echo server banners or account names.
- `test-email.bat` / `scripts/check_email.py` print only whether the password is set and how many characters it has, and mask the user name.
- Tests: `tests/test_notifications.py` covers STARTTLS-before-login, refusal of unencrypted login, Gmail app-password spaces, problem messages without secrets, nine error classes mapped to fixed hints, and that a failed alert logs a code and not the error text. These tests use a stand-in mail server; a real send needs your own login and is checked with `test-email.bat`.

## Settings (all optional)
`REMINDERS_ENABLED` (true), `REMINDER_HOURS_BEFORE` (48), `REMINDER_CHECK_MINUTES` (15), `SMTP_*`, `APP_URL`.

## Security and design notes (for the report)
- Email text only contains the owner's own task titles; the HTML part is escaped; the `email.message` library rejects header injection.
- `POST /notifications/test` and `/check-now` share a limit of 5 per 10 minutes per user, so they cannot be used to spam an inbox.
- The SMTP password is read from `.env` only and is never returned by any endpoint.
- Tests: `tests/test_notifications.py` (window, once-only, opt-out, retry, one-email-per-user, outbox mode, HTML escaping, header injection).
