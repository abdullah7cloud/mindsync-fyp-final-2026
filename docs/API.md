# MindSync API reference (v0.7.0)

Base URL (local): `http://127.0.0.1:8000`. Interactive docs while the backend runs: `/docs`. Machine-readable spec: `docs/openapi.json`
(Postman: *Import -> File -> openapi.json*). Routes marked "login" need `Authorization: Bearer <token>`.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | /health | Liveness check | public |
| POST | /auth/register | Create account, returns JWT | password 8-128 chars with a letter and a number; 409 if the email exists; 20/hour/IP |
| POST | /auth/login | Log in, returns JWT | 5 failures / 15 min per email+IP -> 429 + Retry-After |
| POST | /auth/forgot-password | Ask for a password-reset link by e-mail | body `{email}`; ALWAYS the same 200 answer whether or not the address is registered; link valid 30 minutes, works once; 5 requests / 15 min per email+IP and 100 / hour per IP -> 429; the e-mail is sent after the answer |
| POST | /auth/reset-password | Choose a new password with the e-mailed link | body `{token, new_password}`; same password rules as sign-up; 400 for an unknown, used or expired link; 10 bad attempts / 15 min per IP -> 429 |
| GET | /auth/me | Current user | login; never returns the password hash |
| GET / POST | /tasks | List / create own tasks | login; title 1-200, difficulty 1-5, deadline ISO date-time |
| GET / PATCH / DELETE | /tasks/{id} | Read / edit / delete own task | other users' tasks return 404; responses include `completed_at` (set when status becomes `completed`, cleared when it returns to `pending`) |
| GET | /account/export | Download all your data as JSON (tasks, energy check-ins, wellbeing results, feedback) | login; never includes the password hash |
| POST | /account/password | Change the password while logged in | login; body `{current_password, new_password}`; wrong current password -> 403 and counts toward the lock-out; new password must differ; 204; the owner gets a "password changed" e-mail |
| DELETE | /account/wellbeing | Erase saved wellbeing results only | login; 204 |
| DELETE | /account | Delete the account and all its data permanently | login; body `{password}` must match; a wrong password counts toward the lock-out; 204 |
| POST | /feedback | "Was this recommendation helpful?" `{helpful, energy, difficulty, hours_left}` (no task text stored) | login; 60/hour/user |
| GET | /feedback/summary | `{total, helpful, helpful_percent}` of your own answers | login |
| GET / POST | /energy-checkins | Last 20 / log energy 1-5 | login |
| GET | /recommend | Ranked pending tasks + top task + local explanation | login; see below |
| GET | /wellbeing/model | Questionnaire + metrics of the trained wellbeing model, or `{available:false}` | public |
| POST | /wellbeing/assess | `{answers:{...}}` -> `{label, probabilities, confidence, factors_up, factors_down, disclaimer}`; saves the result | login; 20/hour/user; 422 on invalid answers; 503 if the model is not trained |
| GET | /wellbeing/history | Own past results (newest first) | login |
| POST | /planner/plan | Study planner `{category, energy, stress_risk?, available_minutes?, topics[]}` | login |
| GET | /models/status | Model cards: algorithm, training data, held-out scores, limitations, `external_ai_used:false` | public |
| GET | /notifications/status | Email-alert setting and delivery mode | login |
| PATCH | /notifications/settings | `{email_alerts: bool}` | login |
| POST | /notifications/test, /notifications/check-now | Test email / run the 2-day check now | login; 5 per 10 min |
| POST | /smart/plan | Task-aware plan `{title, details?, deadline?, deadline_hour?, today?, daily_minutes?, today_minutes?, energy?, stress_risk?, answers?, skipped?}` -> `{status:"needs_info", questions[]}` (at most 3) or `{status:"plan", understanding, difficulty, workload, schedule, uncertainties, advice, first_step, inputs_used, limits}` | login; answer keys are whitelisted (kind, scope, progress, skill, deadline, daily_minutes, prior, resources, size); history is read from the database |
| POST | /smart/outcome | How long a finished task really took `{kind, raw_minutes, actual_minutes, felt?, predicted_personal?}` (numbers only) | login; 201 |
| POST | /smart/session | One study session `{kind, minutes 5-600, completed, focus?}` | login; 201 |
| GET | /smart/learned | What MindSync has learned per kind of work (tasks logged, typical ratio, estimate adjustment, preferred session length) | login |
| PUT | /smart/skills/{kind}?level=1-5 | The student's own experience rating for a kind of work | login; 422 outside 1-5 |
| POST | /demo/smart/plan | Guest version of /smart/plan; the browser also sends `skills` and `history{outcomes<=200, sessions<=300}`; nothing is stored | public; 120 calls / 10 min / IP |
| POST | /demo/recommend | Guest ranking from tasks in the body (nothing stored) | public; <= 25 tasks; 120 calls / 10 min / IP |
| POST | /demo/planner/plan | Guest study planner | public; same limits |
| POST | /demo/wellbeing/assess | Guest wellbeing check (result kept only in the browser) | public; same limits |

## GET /recommend response
```
{
  "ranked_tasks": [ { "task": {...}, "score": 0.81,
        "score_breakdown": { "deadline_score", "energy_match_score", "heuristic_score", "ml_score", "ml_weight" } } ],
  "top_task": {...} | null,
  "explanation": "text built by local rules",
  "explanation_source": "local_rules" | "no_tasks",
  "burnout_mode": true | false,
  "burnout_reason": "low_energy" | "high_stress_risk" | null,
  "ml_model": "logistic_regression" | null
}
```
Ranking (update 19, `SMART_RANKING=true` by default): urgency = 0.4 x deadline + 0.6 x work pressure, where work pressure = 1 - exp(-2 x remaining effort / time available); score = 0.6 x urgency + 0.4 x fit between difficulty and current energy. `score_breakdown` also carries the estimate used and its source. With `SMART_RANKING=false` the old rule applies: 0.6 x deadline urgency + 0.4 x energy match. The experimental task-fit model is **off by default** (`ML_ENABLED=false`: `ml_model` and `ml_score` are `null`); if switched on, `ML_WEIGHT` (default 0.3) blends it in. Burnout Mode hides tasks with difficulty > 2
when the latest energy is <= 2, or when the latest wellbeing result (within 14 days) is "High".

## Error codes
401 not logged in / bad token - 404 not found or not yours - 409 email already registered - 422 validation failed - 429 too many attempts - 503 wellbeing model not trained.

## Settings (backend/.env)
DATABASE_URL, JWT_SECRET, SMART_RANKING, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ML_ENABLED, ML_WEIGHT, FRONTEND_ORIGIN, plus the SMTP settings for email alerts.

## Added in update 24 and 25 (My Tasks, reminders, AI Learning Studio, profile)

`docs/openapi.json` was regenerated from the running code in update 25 and now lists every route, including the Smart Planner (`/assist/...`). All routes below need a login unless marked guest. Another student's ids always return 404. Nothing here sends e-mail or calls AI unless said.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | /roadmap | The whole saved roadmap and its view: summary ("Day N of total", done / partly / overdue counts, percent of planned minutes confirmed), today, tomorrow, every day, completed, overdue / delayed, deadline cards, subjects | percent = confirmed minutes / planned minutes (effort, not mastery) |
| GET | /roadmap/history | The change history (confirmations, edits, moves, additions, removals, replans) | login |
| POST | /roadmap/items/{id}/confirm | Say what happened: `{status: done / partial / not_done / delayed, actual_minutes, felt, remaining_minutes, new_day}` | minutes 1-600; partly done must be less than planned; changing an answer replaces the old one; updates the learning record |
| POST | /roadmap/items/{id}/undo | Undo a confirmation, delay or "not done" | restores the earlier state |
| POST | /roadmap/items/{id}/move | Move a block to another day | not for confirmed blocks; not in the past; warns if after the deadline |
| PATCH | /roadmap/items/{id} | Edit title, subject, what you will do, minutes, day | marks the block "Yours" |
| POST | /roadmap/items | Add your own block | needs a plan; day not in the past |
| DELETE | /roadmap/items/{id}?confirm=true | Remove a block | needs `confirm=true`; confirmed blocks cannot be removed |
| POST | /roadmap/replan/preview | What a new plan would keep and replace | changes nothing |
| POST | /roadmap/replan/apply | Replace the remaining plan | body `{confirm: true, reason}` required; confirmed history is kept |
| GET | /reminders | In-app daily and deadline reminders, unread count and a note that nothing is e-mailed | created once per key, never duplicated |
| POST | /reminders/{id}/read, /reminders/read-all | Mark reminders read | |
| POST | /account/email | CLOSED since update 28 | always answers 410 GONE; changing the e-mail now needs a confirmation code: use `POST /my/email/start` and `/my/email/confirm` |
| PUT / GET | /profile | Picture (preset name only), full name, display name, phone, study details | phone digits / spaces / + ( ) - only; unknown fields refused |
| GET | /studio/status | Is AI on, limits, what is left today and this month | never returns a key; says "AI is not switched on" when it is off |
| POST | /studio/sample | Save the hand-written sample pack | no AI; labelled not AI |
| POST | /studio/extract | Read text from a PDF / DOCX / PPTX / TXT / MD upload | 5 MB, type and content checked, plain text only; file name reduced to its last part |
| POST | /studio/packs | Create a pack from text (the ONE AI request) | refused with 409 when AI is off; consent, size, duplicate, cooldown, daily / monthly / global and budget guards run before any request |
| GET | /studio/packs, /studio/packs/{id} | List packs / open one with its lessons | |
| DELETE | /studio/packs/{id}?confirm=true | Delete a pack and its progress | needs `confirm=true` |
| POST | /studio/packs/{id}/quiz | Start a quiz `{count: 5/10/15, difficulty, retry_attempt_id}` | the questions sent have no answers |
| POST | /studio/packs/{id}/quiz/submit | Mark a quiz on the server | returns score, explanations, lessons to revise; saved as an attempt; no AI |
| GET | /studio/packs/{id}/cards?mode=due or all | Flashcards | |
| POST | /studio/cards/{id}/review | Rate a card easy / okay / difficult | moves it between spaced-repetition boxes; no AI |
| GET | /studio/packs/{id}/progress, /studio/summary | Quiz and flashcard progress / the Dashboard summary | |
| POST | /demo/assist/roadmap | Guest: the roadmap view computed from the browser's own blocks | nothing stored; at most 1,500 blocks and 60 tasks |
| GET | /demo/studio/sample | Guest: the sample pack as public data | |

## Update 26 - the four-page version (`/study/*` and `/notebook/*`)

The four pages use these new routes. The older routes above are still in the backend (and still tested) but the website no longer calls them. Every route needs a login (JWT); another student's id always gives 404.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| POST | /study/plans | Make a study plan from the one form `{subject, topic, goal, target_date, mood: good/okay/tired, stress: low/medium/high, timezone}` | AI on and reachable: the AI writes roadmap + tasks, MindSync checks them (3-40 tasks, dates from today to the target date, 10-180 minutes, times 06:00-23:00, daily cap, plain text only); otherwise (or if the check fails) the built-in engine makes the plan. The answer says which one made it (`source: ai / offline`, `note`). 8 plans per 10 minutes per student, 30 plans, 600 tasks |
| GET | /study/plans | All my plans with their tasks | |
| PATCH / DELETE | /study/plans/{id} | Edit subject, topic, notes, target date, roadmap text / delete the plan and its tasks | a new target date before pending tasks returns a `warning` |
| PATCH / DELETE | /study/tasks/{id} | Edit title, details, date, time, minutes, `done` / delete one task | unknown fields refused (422) |
| GET | /study/dashboard?tz= | Totals, completed, remaining, progress %, upcoming deadlines, overdue tasks, task list | "today" uses the browser's time zone |
| GET / POST | /notebook/notes (`?q=` search) | List / create a note `{title, body}` | title 1-120 chars, body up to 60,000, 500 notes; search is literal (% and _ are not wildcards) |
| GET / PATCH / DELETE | /notebook/notes/{id} | Open / edit / delete a note | |
| GET | /notebook/notes/{id}/download?format=pdf or docx | Download a note as PDF (reportlab) or Word (python-docx) | attachment, nosniff |
| GET / POST | /notebook/documents | List / upload (.pdf .docx .pptx .txt, up to 10 MB, 40 documents) | the content must really be that file type |
| PATCH / DELETE | /notebook/documents/{id} | Rename (file type kept) / delete | |
| GET | /notebook/documents/{id}/download, /view | Download / show a PDF inside the page | always attachment, except a PDF shown by the browser's own viewer |
| GET | /notebook/documents/{id}/text | The readable text of a document | used for the quiz and for viewing Word / PowerPoint files; scanned pages give a clear 422 |
| GET / POST | /studio/status, /studio/extract, /studio/packs, /studio/packs/{id}/quiz, /studio/packs/{id}/quiz/submit | Reused unchanged for the AI Learning Zone quiz | AI off: a clear "not available" message and no fake quiz |


## Update 28 - My Profile and Settings (`/my/*`)

All routes need a login. They are new; no earlier route changed (except `/account/email`, now closed, see above).

| Method | Path | What it does | Notes |
|---|---|---|---|
| GET / PUT | /my/profile | Read or save the full name; also returns the e-mail, whether a picture exists and its version | name 1-100 characters, trimmed; unknown fields refused |
| POST | /my/email/start | Ask to change the sign-in e-mail: `{new_email, password}` | wrong password -> 403 and counts toward the lock-out; the answer is the same whether or not the address is taken (and then nothing is sent); a 6-digit code is e-mailed to the NEW address; max 3 requests per hour; the code is stored only as a keyed hash and lives 15 minutes |
| POST | /my/email/confirm | `{code}` | 5 wrong tries cancel the request; on success the e-mail changes and the OLD address gets a notice |
| POST | /my/email/cancel | Forget a pending change | |
| POST | /my/avatar | Upload a picture (multipart field `file`) | max 10 uploads per hour; JPEG, PNG or WebP, 3 MB; the server re-draws it as a 256 x 256 JPEG (hidden data and EXIF removed; huge-image guard) |
| GET / DELETE | /my/avatar | Download or remove your picture | only the owner can read it |
| GET / PUT | /my/settings | Reminder switch, `remind_percent` (30 or 35), time zone | reminders are OFF by default; time zone must be a real IANA name; also returns `delivery` ("email" or "demo") and `percent_choices` |
| POST | /my/settings/test-email | Send yourself one test reminder e-mail | max 3 per hour |

Password change still uses the earlier route `POST /account/password`.

### Reminder rule
The deadline is the end of the due day (23:59) in the student's time zone. The reminder time is `deadline - (deadline - task created) x percent / 100`. Example: a task made 10 days before its deadline with 30 percent is reminded when 3 days remain. One e-mail per task and due date (database unique key on task and due date). Finished and deleted tasks never get one. Changing a task's due date makes a new reminder possible for the new date.
