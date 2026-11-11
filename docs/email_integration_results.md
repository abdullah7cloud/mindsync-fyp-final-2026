### E-mail reminders against a local mail-collecting server, 2026-10-29 04:40

**21 / 22 checks passed.** Real smtplib code, real database, real reminder cycle; the mail server is a local receiver, so nothing was sent to the internet and live delivery by a real provider (for example Gmail) is NOT covered.

| Check | Result |
|---|---|
| a task due in 40 h gets one e-mail through a real SMTP connection | PASS |
| it is addressed only to its owner and names the task | PASS |
| the log says 'sent' (accepted by the mail server), not 'delivered' | PASS |
| running the job again does not send the same reminder twice | PASS |
| moving the deadline re-arms the reminder (a new e-mail for the new deadline) | PASS |
| and the new e-mail shows the new deadline | FAIL |
| same-day reminder is NOT sent before the student's chosen hour in their own time zone | PASS |
| same-day reminder arrives after the chosen hour, even though it is still the 29th in UTC | PASS |
| the time in the e-mail is the student's local time (18:00 in Auckland), not UTC | PASS |
| the subject says it is due today | PASS |
| the same-day reminder is sent once per day | PASS |
| overdue reminder is sent for a task 5 hours late, and not for one 5 days late | PASS |
| a task created 10 h before its deadline with three lead times sends ONE e-mail | PASS |
| no e-mail for a student who switched alerts off, one whose reminders are off, or a finished task | PASS |
| a task title with line breaks cannot add e-mail headers or recipients | PASS |
| markup in a title is escaped in the HTML part | PASS |
| mail server down: the cycle survives and records 'failed' with a short code (no server text, no secrets) | PASS |
| it does not hammer the server: no retry within 15 minutes | PASS |
| after 15 minutes it retries, the e-mail arrives and the log shows sent with 2 attempts | PASS |
| a refused mail login is recorded as 'failed: auth' and the password is not stored anywhere | PASS |
| the hint shown to the student is a fixed sentence without the server's own text | PASS |
| with no mail server the reminder is saved as a file and logged 'outbox', never 'sent' | PASS |

### E-mail reminders against a local mail-collecting server, 2026-10-29 04:40

**22 / 22 checks passed.** Real smtplib code, real database, real reminder cycle; the mail server is a local receiver, so nothing was sent to the internet and live delivery by a real provider (for example Gmail) is NOT covered.

| Check | Result |
|---|---|
| a task due in 40 h gets one e-mail through a real SMTP connection | PASS |
| it is addressed only to its owner and names the task | PASS |
| the log says 'sent' (accepted by the mail server), not 'delivered' | PASS |
| running the job again does not send the same reminder twice | PASS |
| moving the deadline re-arms the reminder (a new e-mail for the new deadline) | PASS |
| and the new e-mail shows the new deadline | PASS |
| same-day reminder is NOT sent before the student's chosen hour in their own time zone | PASS |
| same-day reminder arrives after the chosen hour, even though it is still the 29th in UTC | PASS |
| the time in the e-mail is the student's local time (18:00 in Auckland), not UTC | PASS |
| the subject says it is due today | PASS |
| the same-day reminder is sent once per day | PASS |
| overdue reminder is sent for a task 5 hours late, and not for one 5 days late | PASS |
| a task created 10 h before its deadline with three lead times sends ONE e-mail | PASS |
| no e-mail for a student who switched alerts off, one whose reminders are off, or a finished task | PASS |
| a task title with line breaks cannot add e-mail headers or recipients | PASS |
| markup in a title is escaped in the HTML part | PASS |
| mail server down: the cycle survives and records 'failed' with a short code (no server text, no secrets) | PASS |
| it does not hammer the server: no retry within 15 minutes | PASS |
| after 15 minutes it retries, the e-mail arrives and the log shows sent with 2 attempts | PASS |
| a refused mail login is recorded as 'failed: auth' and the password is not stored anywhere | PASS |
| the hint shown to the student is a fixed sentence without the server's own text | PASS |
| with no mail server the reminder is saved as a file and logged 'outbox', never 'sent' | PASS |

### E-mail reminders against a local mail-collecting server, 2026-10-29 05:01

**22 / 22 checks passed.** Real smtplib code, real database, real reminder cycle; the mail server is a local receiver, so nothing was sent to the internet and live delivery by a real provider (for example Gmail) is NOT covered.

| Check | Result |
|---|---|
| a task due in 40 h gets one e-mail through a real SMTP connection | PASS |
| it is addressed only to its owner and names the task | PASS |
| the log says 'sent' (accepted by the mail server), not 'delivered' | PASS |
| running the job again does not send the same reminder twice | PASS |
| moving the deadline re-arms the reminder (a new e-mail for the new deadline) | PASS |
| and the new e-mail shows the new deadline | PASS |
| same-day reminder is NOT sent before the student's chosen hour in their own time zone | PASS |
| same-day reminder arrives after the chosen hour, even though it is still the 29th in UTC | PASS |
| the time in the e-mail is the student's local time (18:00 in Auckland), not UTC | PASS |
| the subject says it is due today | PASS |
| the same-day reminder is sent once per day | PASS |
| overdue reminder is sent for a task 5 hours late, and not for one 5 days late | PASS |
| a task created 10 h before its deadline with three lead times sends ONE e-mail | PASS |
| no e-mail for a student who switched alerts off, one whose reminders are off, or a finished task | PASS |
| a task title with line breaks cannot add e-mail headers or recipients | PASS |
| markup in a title is escaped in the HTML part | PASS |
| mail server down: the cycle survives and records 'failed' with a short code (no server text, no secrets) | PASS |
| it does not hammer the server: no retry within 15 minutes | PASS |
| after 15 minutes it retries, the e-mail arrives and the log shows sent with 2 attempts | PASS |
| a refused mail login is recorded as 'failed: auth' and the password is not stored anywhere | PASS |
| the hint shown to the student is a fixed sentence without the server's own text | PASS |
| with no mail server the reminder is saved as a file and logged 'outbox', never 'sent' | PASS |

