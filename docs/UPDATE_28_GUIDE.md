# MindSync Update 28 - My Profile, Settings and e-mail reminders

Update 28 adds **two pages only**. The four main pages (Dashboard, Study Planner, AI Learning Zone, My Notebook) were not redesigned and their files were not changed. The left menu shows those four pages first, then My Profile and Settings right after My Notebook (the "My account" window still links to them too).

## What is new

**My Profile**
- Change your full name.
- Upload, change or remove a profile picture. The server re-draws every picture as a small safe JPEG (256 x 256), so hidden data inside a file is removed.
- Change your sign-in e-mail with a check: type your password, MindSync e-mails a 6-digit code to the NEW address, you type the code. The old address gets a notice that the e-mail was changed.
- Change your password (same safe rules as before).
- Every save shows a clear message.

**Settings**
- Appearance: Light, Dark or System default. The choice is remembered on that device.
- E-mail reminders: a switch (OFF until you turn it on) and a choice of 30 percent or 35 percent of the time left. Example: a task with 10 days to finish and 30 percent gives an e-mail when 3 days remain.
- Time zone (your deadlines end at 23:59 on the due day in that zone).
- A "Send me a test e-mail" button.

## How the reminders work (simple version)
1. The MindSync backend has a small timer inside it. Every 5 minutes it looks at every student who switched reminders on.
2. For each unfinished task it works out the reminder moment. Reminder moment = deadline minus (time between creating the task and the deadline) x 30 percent (or 35 percent).
3. If that moment has passed and the deadline has not, it sends ONE friendly e-mail with the task name, the deadline and how much time is left (tasks that come due together are listed in one e-mail).
4. It writes a "sent" record first, protected by a unique database rule (one per task and due date). So even if two backends run by mistake, only one e-mail is sent.
5. Finished or deleted tasks never get an e-mail. If you change a task's due date, the reminder is worked out again for the new date. If sending fails, it tries again every 15 minutes, at most 5 times.

## Do reminders need an always-running server? Yes.
The reminders are sent by the **backend**, not by the browser. So the website does **not** need to be open, but the **backend must be running** (on your laptop that means the black backend window is open, and the laptop is awake). If the backend is off at the reminder time, the e-mail is sent as soon as the backend starts again, as long as the deadline has not passed. For real students you would host the backend on a server that stays on (that is a choice for later and may cost money; nothing was bought).

## Do reminders need extra setup to reach a real inbox? Yes, once.
Without a mail account, MindSync is in "demo mode": each e-mail is saved as a small `.eml` file in `backend/outbox/` and the Settings page says so. To send real e-mails, you put your own mail account in `backend/.env` (never in a chat):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@gmail.com
```
For Gmail you need 2-Step Verification and an App Password (see docs/EMAIL_ALERTS.md). Settings that control the timer: `TASK_REMINDERS_ENABLED` (default true) and `TASK_REMINDER_CHECK_MINUTES` (default 5).

## What was tested (in the test sandbox, not on your laptop)
- Backend: 594 automated tests pass (all earlier tests plus 55 new ones: 38 for profile, e-mail change, pictures, settings and the reminder rule, duplicates, retries, time zones and two schedulers at once, and 17 for the preview safety check). They need `TZ=UTC` in this sandbox only.
- Website: 55 automated tests pass and the production build works.
- Real browser test of the new pages: 35 of 36 checks passed. The 36th was a harmless browser "aborted" note after a successful password change (the server answered 204 OK).
- Real browser test of the old four pages against Update 28: 62 of 62 (AI stand-in) and 58 of 58 (AI off).
- A real scheduled reminder was sent automatically by the running backend with the website closed, and a second check sent nothing more.

## What was NOT tested
- Delivery to a real inbox through a real mail server (no mail account was available). The e-mail code path to a mail server is the same one Update 26 already uses for password reset, but it was not run against a real server for this update.
- Running Update 28 on your laptop (it has not been installed yet).

## Safety notes
- New tables only (u28_pictures, u28_preferences, u28_email_changes, u28_task_reminders); no existing table was changed. They are created automatically at start and are listed in `database/schema.sql`.
- Deleting your account also deletes the picture, settings, pending e-mail change and reminder records. "Download my data" includes your profile and settings.
- The old route `POST /account/email` (password only) is now closed with 410, because e-mail changes need the code.
- Secrets stay in backend environment variables. The picture is only readable by its owner.

## Fix added after the first preview request: "Invalid or expired token"
A MindSync login lasts 60 minutes. If a page (for example the Study Planner) stayed open longer, the next click showed the raw message "Invalid or expired token". Now MindSync signs you out and opens the login page with the note "Your login has ended for safety. Please log in again." (Files: `frontend/src/api.js`, `context/AuthContext.jsx`, and the one-time note on `LoginPage.jsx`, which is now also kept visible while you type.) Tested with a 1-minute login in a real browser. The page designs did not change.
