# MindSync update 20: evaluation, old version against upgraded version

Date of measurements: 29 October 2026. Every number below was produced by running the code in this project. "Old" is the project exactly as it was before the upgrade (backed up before any change). Nothing here comes from real students: no usability session has been run yet, so there are no user-satisfaction, SUS or accuracy-against-reality figures, and none are claimed.

## 1. Automated tests

| Suite | Old | Upgraded |
|---|---|---|
| Backend (pytest) | 220 passed | 319 passed |
| Frontend (Vitest) | 109 passed | 139 passed |
| Browser end-to-end (Playwright, real browser against the running app) | 135 checks passed (recorded when the previous update was built) | 162 checks passed |
| Live security probe (OWASP Top 10 categories) | 60 of 60 checks passed on its last recorded run | 95 of 95 checks passed |

The old end-to-end script drove the six old pages, so it could not be run unchanged against the new app; the upgraded script covers the guest journey (describe, understand, evaluate, accept, timer, feedback, low energy, replan offer, calendar, dashboard, history, wellbeing, toolkit, settings, profile), the account journey (register, planner on the server, edit and finish tasks, settings and profile effects, export, wrong and right password deletion), password reset, phone layout, photos and basic accessibility.

Bugs the new tests found while writing them (all fixed, each with a regression test):

1. The guest Dashboard returned a server error as soon as a guest had a task or a logged session (a helper was called under the wrong name).
2. Guests' cheap calculation calls shared a small per-IP limit with model calls, so an active guest, or a whole class behind one network address, could be told "too many requests". They now have their own larger allowance.
3. The public model-status page said no external AI was used, which would have been false once a key is set. It now reports the real configuration.
4. The free-text task reader returned a whole sentence as a task title (fixed in the earlier segment; the test expectation was updated).

## 2. Same input, both versions

Input: three tasks, all due in three days (a 1,500-word report, a Python assignment with tests, revision for a database exam), 60 minutes of study a day, energy 3. The old planner takes one task at a time, so each was submitted separately (the two follow-up questions it asked were skipped, as a student in a hurry could).

| | Old (three separate plans) | Upgraded (one evaluation) |
|---|---|---|
| Workload estimate, likely (minutes) | 895 / 480 / 480 | 895 / 480 / 480 |
| Time the plan treats as available | 240 minutes for each task (the whole window to itself) | 225 minutes in total for all three |
| Verdict | each task alone reports "does not fit", shortfalls 720 / 255 / 300 | one verdict "does not fit", shortfall 1,630 minutes |
| Minutes put onto the same 240 minutes | 1,855 | 1,855 needed against 225 available, reported as one shortfall |
| What it offers | per-task advice | an alternative that was verified by re-running the scheduler ("ask for more time": extend to 29 November) |

What this shows: the estimates are the same, so the upgrade does not make the numbers more "accurate"; what it changes is that the old version never added the three tasks together, so the student would have seen three separate partial problems and no sign that their week was impossible. The 15-minute difference in capacity (240 against 225) is probably because I gave the new version a deadline hour (20:00) and the old one no hour; I did not investigate further.

Not measured: whether either version's estimates match how long real students take. The upgraded version can learn from logged sessions; with no real sessions yet there is nothing to compare.

## 3. Speed (target in the project brief: under 3 seconds end to end)

Measured with `scripts/benchmark_latency.py api` (50 requests each, one signed-in user with 20 tasks) against the backend running in the cloud test machine with SQLite and the mock AI provider.

| Endpoint | Median ms | p95 ms | Max ms |
|---|---|---|---|
| POST /assist/understand (local rules) | 16.9 | 21.9 | 54.9 |
| POST /assist/evaluate (3 drafts + 20 saved tasks) | 21.2 | 30.5 | 72.8 |
| GET /assist/state (plan, today, replan check) | 13.5 | 18.7 | 20.9 |
| GET /assist/dashboard | 17.3 | 24.2 | 30.7 |
| POST /assist/session (feedback learning) | 15.5 | 19.7 | 24.3 |
| POST /demo/assist/plan (guest, 10 tasks) | 12.9 | 14.0 | 21.1 |
| GET /recommend, 10 students at once (100 requests) | 249.2 | 307.2 | 368.5 |

All are far below 3,000 ms. Caveats: this is a different machine and database from the student's laptop with PostgreSQL, and the old version was not re-benchmarked on this machine, so I do not claim the upgrade is faster or slower than before. A real language-model call (understand, explain, ask, review) adds the provider's response time, which has not been measured; the code stops waiting after 20 seconds and falls back to the rules, and the planning calculation itself never waits for the model.

## 4. Size

| | Old | Upgraded |
|---|---|---|
| Backend application code (Python lines) | 4,800 | 8,397 |
| Frontend code (JSX + JS lines, excluding tests) | 4,465 | 7,177 |
| API routes | 38 | 63 |
| Pages in the menu | 6 | 5 |
| Photo-banner pages | 4 | 3 |

Lines of code say how much was added, not how good it is.

## 5. Findings from the audit that the upgrade addresses (A1 to A10 in `AUDIT_2026-10-29.md`)

| Finding | Status | Evidence |
|---|---|---|
| A1 planners not connected to the task list | Fixed | Section 2; end-to-end checks "Evaluate checks it against the rest of the plan", "Accepting adds the task" |
| A2 timer not tied to a task | Fixed | e2e "Starting a block opens the Focus tab linked to that block", session feedback tests |
| A3 energy does not re-plan | Fixed (offer, not automatic) | e2e "Very low energy offers a lighter plan (and does not change it by itself)" |
| A4 deadline change does not touch plans | Fixed | scheduler/API tests for the replan reasons |
| A5 fixed 48-hour e-mail | Fixed in code; real delivery untested | `test_reminders_v2.py` (13 tests) |
| A6 settings only an on/off switch | Fixed | e2e "Changing study minutes makes the planner offer an updated plan" |
| A7 no profile | Fixed | e2e "A weekly goal set in My Profile appears on the Dashboard" |
| A8 counts only on the dashboard | Fixed (real data only) | History charts and weekly review; empty states when there is no data |
| A9 no external language model | Added, optional; not tested against the live service | Section 4 of the architecture document |
| A10 not connected, no evaluate step | Fixed | one page: describe, understand, evaluate, accept |

## 6. What was not done or not tested

- Live OpenAI call (no key here).
- Real e-mail delivery.
- Usability test with students, SUS score, and any claim about learning outcomes or burnout reduction.
- Screen-reader testing.
- Running the new test suites on the student's laptop (`run-tests.bat`, `run-e2e.bat`) and the PostgreSQL production path; automated tests here use SQLite.
- Optional extras from the brief that were deliberately left out: a push-style notification centre and calendar file export. What exists: calendar view, focus mode and session-linked timer, assignment breakdown into stages, exam revision handling through the task taxonomy, weekly review, weekly goal, feasibility warning, "Explain my plan", guest mode.
