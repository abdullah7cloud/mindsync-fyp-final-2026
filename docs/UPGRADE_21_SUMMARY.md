# MindSync update 21 - what changed, what was tested, what is still open

Date of measurements: 29 October 2026. Every number comes from running the code in this project in the build environment (SQLite, Linux, no
real OpenAI call, no real mail provider). Numbers on your laptop with PostgreSQL will differ; re-run the `.bat` files there and quote **your own logs** in the report.

## 1. What is new since update 20

| Area | Change | Evidence |
|---|---|---|
| OpenAI integration | Uses the verified current cheapest model (`gpt-6-luna`, 0.10 / 0.50 US dollars per million input / output tokens, checked on OpenAI's pages on 29 Oct 2026). Sends `reasoning_effort: none` (the default "medium" is billed and slower), a token cap, no sampling parameters, a 25 s total wait cap, 2 retries on timeout / 429 / 5xx. Discards truncated and refused answers. Model-written text containing links, markup, key-like strings or instructions the student did not type is rejected. | `ai_integration_results.md` (18/18 against a local stand-in), `test_ai_layer.py` |
| Cost control | Provider configured -> student allows AI -> guests never reach the model -> 40 calls per student per day -> 5 USD per month -> call -> validate -> record tokens and cost in `ai_usage`. Any failure falls back to local rules and the screen says which one wrote the text. | `docs/diagrams/ai_guard_flow.png`, probe checks 15-17 |
| E-mail reminders | One wording for every reminder (digest style), same-day reminders at the student's hour in the student's time zone, overdue reminders, duplicates prevented by a unique key (task + kind + deadline), failed sends retried after 15 minutes up to 5 times, "sent" only when the mail server accepted the message, otherwise "outbox". Tested against a local SMTP sink. | `email_integration_results.md` (22/22) |
| Estimates | Ranges such as "chapters 1 to 6" and "5 to 8 pages", talk minutes for presentations, no double counting of chapters and pages, due dates and "I have to" no longer counted as work, day words removed from titles, floor against under-estimating when the size is unknown. | `UPGRADE_21_INTELLIGENCE.md` |
| Scheduler | A task is "tight" only if it has no slack and uses at least half of its own window; 5-minute fragments are merged into the neighbouring block. | `test_assist_scheduler.py` |
| Free text | One line with several tasks is split only where a new task really starts ("..., and a 1500 word report due in 6 days. Also read ..."); a continuation such as "I find integration really hard" stays with its task. | `test_assist_api.py` |
| Screens | Day bars show "20m" / "1.5h" with units; milestones no longer repeat the date; the report fades in (reduced-motion respected); calendar and chart accessibility fixed (see 3). | screenshots in `e2e_screenshots/` |
| Windows | `tzdata` added to requirements (Windows has no time-zone database). New batch files: `run-ai-test`, `run-email-test`, `run-journey-test`, `run-a11y-test`, `run-intelligence-test`. | |

## 2. Test evidence (this build environment)

| Suite | Result |
|---|---|
| Backend unit and API tests (pytest) | 338 passed (SQLite) and 338 passed on PostgreSQL 16 (`MINDSYNC_TEST_DATABASE_URL`) |
| Frontend tests (Vitest) | 140 passed |
| Browser end-to-end in real Chromium (guest and account journeys, phone layout, photos) | 162 / 162 checks |
| Journey probe over HTTP (register, understand, evaluate, accept, low energy, replan, sessions, dashboard, settings, assistant, injection, review, task edit, reminders, guest twin) | 30 / 30 (`journey_results.md`) |
| Live security probe, OWASP Top 10 categories | 95 / 95 (`security_test_results.md`) |
| Accessibility, axe-core WCAG 2.0/2.1 A and AA on 16 page states at desktop and phone size | 0 violations after fixes (`accessibility_results.md`); 10 real violations were found by the first run and fixed |
| OpenAI integration probe (local stand-in) | 18 / 18 |
| E-mail integration probe (local SMTP) | 22 / 22 |
| Task-aware evaluation script | 140 scenarios, 0 constraint violations, 25 / 25 constructed cases correct (baseline 10 / 25) |
| Speed (engine only) | 1000 tasks ranked in a median 7.2 ms; single-user API calls 3-24 ms median and under 125 ms at their worst; 10 simultaneous students p95 248 ms, max 356 ms (target: under 3 s end to end). Laptop PostgreSQL figures: re-run `run-benchmark.bat` |

Defects found by these runs and fixed (each has a regression test): guest dashboard server error; per-IP limit shared between cheap and model calls;
public model card claimed "no external AI"; old-style reminder wording for UTC students; trivial tasks flagged "tight"; large maths exam estimated smaller
than a short quiz; large presentation estimated smaller than a 5-slide one; chapters and pages added together; five-minute fragments; one-line multi-task text
read as a single task; model-written links accepted in a task title; 4 calendar and 3 contrast/scroll accessibility violations.

## 3. Which parts are your own trained models and which are external AI

| Part | What it is | Trained by you? |
|---|---|---|
| Task ranking (urgency 60 % / energy fit 40 %) | transparent formula | n/a (rules) |
| Task-fit model | logistic model trained on **simulated** data, switched off by default | yes, prototype, labelled as simulated |
| Wellbeing model | multinomial logistic regression trained on a public survey dataset; reproduces that dataset's scoring rule | yes; it is not a diagnosis |
| Task understanding, workload, scheduling, feasibility, alternatives | deterministic Python (lexicon, counts, EDF with daily capacity) | rules written by you; history calibration learns per student |
| Natural-language understanding, explanations, weekly review, question answering | **optional external OpenAI model**, off unless you add a key; never decides minutes, order, deadlines or feasibility; every answer validated; rule-based fallback | **no** - external |

Say this plainly in the report and the viva. The honest summary: "MindSync works fully without any external AI. The optional language model only changes wording and reading of free text."

## 4. Limits (also listed in the report and viva material)

- No real OpenAI call, no real SMTP delivery, no run on your laptop or on PostgreSQL has been made by this build. The stand-in tests prove MindSync's side only.
- Estimates (minutes per unit, size multipliers, stage shares) are design assumptions, not validated against real students. They are shown as ranges and adjusted from the student's own history.
- No usability study (SUS), no screen-reader test, no study with real burnout outcomes. The wellbeing model reproduces a dataset's formula; it does not predict burnout.
- Kind detection uses a word list; unusual wording is reported as "unknown" and the app asks.
- The ten-case intelligence run is a smoke test of behaviour, not a statistical evaluation.
