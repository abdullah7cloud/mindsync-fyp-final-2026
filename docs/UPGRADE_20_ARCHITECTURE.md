# MindSync update 20: architecture, AI integration, scheduling, personalisation, database, security, privacy, limitations

Written 29 October 2026. Everything here describes code that exists in this project and tests that were run. Where something could not be tested, it says so.

## 1. What changed, in one paragraph

The app used to have six pages and two separate planners that did not know about each other. It now has five pages (Smart Planner, Dashboard, Student Toolkit, Settings, My Profile) and one connected planner. A student types tasks in their own words, MindSync turns them into task drafts, checks them against everything already planned, shows one report with a verdict, and only then saves the plan. After each study block the student gives short feedback, and that feedback changes later estimates. Energy, deadlines, settings and wellbeing results can each make the planner offer an updated plan; it never changes a plan by itself.

## 2. Which parts are what (so nothing is oversold)

| Part | What it is | Where |
|---|---|---|
| Understanding free text ("I have a stats exam in 10 days...") | Pretrained external language model (OpenAI, optional) with a rule-based fallback. I did not train it. | `backend/app/ai/`, `backend/app/assist/localai.py` |
| Explanations, answers to questions, weekly-review wording | Same language model, same fallback | `app/ai/`, `localai.py` |
| Workload range, difficulty, schedule, feasibility, alternatives | Deterministic Python (earliest-deadline-first with daily capacity). No model. | `app/assist/scheduler.py`, `core.py`, `app/taskaware/` |
| Stress-level estimate | Locally trained logistic regression on a public survey dataset | `app/ml/`, `ml_training/` |
| Personal difficulty, time estimates | Deterministic rules fed by the student's own logged sessions | `core.py` (`logSession` twin in `guest/guestAssist.js`) |
| Settings (study minutes, pacing, buffer days, gentle mode, reminders) | Student choices, applied by the scheduler | `settings_schema.py` |
| Safety rules (workload ceilings, gentle mode, no diagnosis wording, AI output validation) | Fixed rules | `scheduler.py`, `ai/validate`, `ai/sanitize.py` |

The language model never does arithmetic that the student relies on. Its numeric time estimate is only allowed to widen the deterministic range, and only within 0.5x to 2x of it.

## 3. Architecture

```
React (Vite)                                       FastAPI                                   PostgreSQL
 Smart Planner  --/assist/understand-->  [AI layer: guards -> provider -> validate -> record] --> ai_usage
 PlanBuilder    --/assist/evaluate---->  [core: metas, EDF scheduler, feasibility, alternatives]
 Report         --/assist/accept------>  task rows + task_meta + study_plans + plan_sessions
 SessionFeedback--/assist/session----->  task_sessions, task_meta (personal difficulty), outcomes
 ReplanBanner   <--/assist/state-------  replan_check (energy, deadline, settings, wellbeing, behind, tasks)
 Dashboard      <--/assist/dashboard--   summary built from real rows only
 Settings/Profile <--> /settings, /profile (strict schemas)
 Guest mode: same code through /demo/assist/*, state kept in the browser and sent (bounded) with each request
```

One shared front-end data layer (`AppDataContext`) refreshes the planner state after every action, so a finished task, a new deadline, a check-in or a changed setting shows up on every page. PostgreSQL is the source of truth for students; guests keep numbers and their own task titles in the browser only.

## 4. AI integration

Request path for every language-model call, in this order: provider configured? student's "AI assistant" switch on? guest policy (guests never reach the model unless the owner sets `AI_ALLOW_GUESTS=true`)? per-student daily cap (40)? monthly budget (default 5 US dollars, all students)? Then: clean the student's text, wrap it as delimited data, call the provider with an 8 s timeout per attempt, 10 s in total, and up to 2 retries inside that limit (on timeout, 429 or 5xx), validate the answer against a strict JSON schema and content rules, record tokens, cost and outcome in `ai_usage`. Any failure returns "use the rules" and the screen says which source wrote the text ("Written by the AI assistant" or "Written by MindSync's rules").

The key is read only from `backend/.env` on the server. It is never sent to the browser, never logged, and never returned by any endpoint (a probe check confirms the usage endpoint contains no key). Default model: `gpt-6-luna` (reasoning and price in `AI_MODEL_SELECTION.md`). With no key, or `AI_PROVIDER=off`, the whole product works with rules only.

What I could not test: a call to the real OpenAI service. There is no key in this environment and I made no purchase. Every test uses a mock provider or an `httpx` mock transport that checks the request shape (strict `json_schema`, bearer header, timeout, retry on 429/5xx, no retry on 4xx). The first real call should be made by the student after adding a key; the Settings page then shows "Connected" and the per-day count.

## 5. Scheduling

Inputs: pending tasks with a remaining-minutes estimate (low / likely / high), deadlines in the student's time zone, priority (important, normal, can wait), settings (weekday and weekend minutes, study days, buffer days, pacing, gentle mode), minutes already studied today.

Method: earliest-deadline-first over the days with capacity, split into blocks sized by the kind of work and the student's block-length preference, with a break pattern. It reports per-task status (on track, tight, will miss), a verdict for the whole set (fits comfortably, fits but tight, does not fit, with the shortfall in minutes), milestones, and notes. Gentle mode lowers the day's capacity when energy is low and starts with the easier block.

Alternatives are never invented by the language model. Each one (add minutes a day, add rest days, reduce scope, extend a deadline, postpone the lowest-priority task, start earlier) is produced by changing an input and running the scheduler again; the report only shows an alternative that the second run confirms.

Replan detection compares the stored plan's inputs with the current ones and gives a reason: new tasks, a changed deadline, changed settings, energy of 2 or lower, a newly High stress estimate, or being behind. The student sees what would change, day by day, and presses "Update my plan" or "Keep my plan as it is".

## 6. Personalisation (what learns, and from what)

Only logged data is used. After a block the student can give minutes, focus (1-5), how hard it felt (1-5), how the length felt, energy after, whether the task is finished, and minutes left.

- Personal difficulty moves by an exponential average (0.8 old, 0.2 new) of "how hard it felt".
- Minutes done are added to the task; if the student says how much is left, their number wins over the estimate.
- Finishing a task stores the real total as an outcome; later estimates for that kind of work are calibrated from outcomes.
- "Too short" or "too long" answers are counted; after several similar answers the block length for that kind of work changes.
- Energy after a block of 2 or lower makes the planner offer a lighter plan.

Free-text profile fields (about me, goals, strengths, struggles) are for the student only and are not sent to the language model. The Profile page lists what was learned and from how many sessions.

## 7. Database design

New tables only (no existing table was altered, so an existing database keeps working through `create_all`): `user_settings`, `user_profiles`, `task_meta` (the task's analysis and estimates as JSON, one row per task), `study_plans` (one active plan per student, with its inputs for later comparison), `plan_sessions` (blocks with status planned, done, skipped), `task_sessions` (feedback rows), `ai_usage` (one row per model call: tokens, cost, outcome, no prompt text), `reminder_log` (unique key per task, deadline and reminder type, so a reminder is never sent twice), `weekly_reviews`. All rows carry the owner's id and every query filters on it. Export and erase cover all of them.

## 8. Reminders

Choices: how long before (1, 3, 6, 12, 24, 48, 72 or 168 hours), a same-day reminder at a chosen hour, an overdue reminder, and a time zone. Changing a deadline re-arms its reminders. A reminder is recorded as `sent` only when the mail server accepted the message, as `outbox` when mail is in practice mode (written to a local folder, not delivered), and as `failed` with the reason otherwise. The Settings page says plainly which of these applies. I could not send a real e-mail from this environment, so real delivery is untested; the student can test it with `test-email.bat` after adding SMTP details.

## 9. Security

- Server-side secrets only; strict Pydantic schemas with `extra=forbid` for settings and profile (no mass assignment); length and range limits on every field.
- Every student query is owner-scoped; another student's task id returns 404 (checked live).
- Prompt-injection defence: student text is cleaned (control characters, role markers), wrapped in delimiters and labelled as data; model output must match a strict schema; sentences with numbers the facts do not support are rejected; unsafe or off-task content falls back to the rules.
- Abuse limits: per-student and per-IP rate limits, per-student daily AI cap, global monthly AI budget, 10 s total wait, bounded guest state (25 tasks, 300 sessions, clock within 36 hours of the server's).
- Checks: 14 backend tests for the AI layer, 36 for the connected planner API, 17 for the scheduler and 13 for reminders, and a live probe of 95 checks (OWASP Top 10 categories) that passed on 29 October 2026; results are in `docs/security_test_results.md`.

## 10. Privacy

Sent to the language model (only when a key is set, the student's AI switch is on, and the student is signed in): the text the student typed into the planner or assistant, task titles and numbers (minutes, difficulty, deadlines) that the question needs. Not sent: name, e-mail address, password, wellbeing answers, profile free text. Guests keep everything in the browser; the guest planner makes no model call. The `ai_usage` table stores counts, tokens and cost, not the text.

## 11. Limitations (honest list)

1. The real model path (OpenAI) has not been run against the live service.
2. Real e-mail delivery has not been run.
3. The latency figures were measured on a cloud test machine with SQLite, not on the student's laptop with PostgreSQL. They are evidence that the deterministic code is fast, not a laptop benchmark. A real model call adds the provider's response time (up to the 10 s total limit) and was not measured.
4. The estimates come from rules and a small task taxonomy. They have not been validated against real students' times; the first real data will come from the usability study.
5. The stress model reproduces a survey dataset's scoring rule. It does not predict burnout and is not a diagnosis.
6. The Student Toolkit cites published studies. Its "what the research found" and "limits of the evidence" notes are short summaries I wrote, so check each against the paper itself before quoting it in the report.
7. The e-mail time zone and daylight-saving handling is tested in code (`zonedToIso` tests and the reminder tests) but not on a live mail run.
8. Accessibility was checked automatically (labels, names, one h1, focus on dialogs, reduced motion) and visually on phone width. It has not been checked with a screen reader.
9. A guest who signs up keeps their tasks; their plan is rebuilt on the server after they say yes, rather than copied.
