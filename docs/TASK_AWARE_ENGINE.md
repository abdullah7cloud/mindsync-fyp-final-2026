# Task-aware planning engine (update 19) - architecture

Status: written before the code (proposal), then updated with what was built (section 7). Results are in `TASKAWARE_EVALUATION.md`.

## 1. What was wrong (audit of the code before this update)

| Area | Before | Problem |
|---|---|---|
| Duration | `planner.py::mode_for(energy)` gave fixed blocks: 15/10, 20/5, 25/5, 45/10 | The same block and break for every task type; energy was the only input |
| Difficulty | `planner.offline_rate`: a table of ~35 topic names plus easier/harder keywords; the task form asked for a 1-5 slider | No scope, no student skill, no history, no uncertainty |
| Workload | `DEFAULT_MINUTES = {1: 20, 2: 30, 3: 45, 4: 60, 5: 90}` per topic | One number per topic; a software project got 90 minutes at most |
| Task kind | Free-text `category` string, never used by the engine | Programming, maths and reading were planned the same way |
| Ranking | `heuristic.py`: 0.6 x deadline + 0.4 x energy match | Ignored how much work a task needs; a huge project and a 10-minute reading with the same deadline ranked by difficulty only |
| Learning | `RecommendationFeedback` stored yes/no only | Nothing changed future estimates |
| Questions | none | Every input got a plan, even "do my project" |
| Explanation | `explain.py` templates about deadline and energy | Could not explain duration, method or uncertainty |

The wellbeing model (logistic regression on a questionnaire) and the experimental task-fit model (trained on simulated data, off by default) do **not** understand task content. They are not used to judge task complexity and the documentation says so.

## 2. Design principle: which parts need machine learning?

| Component | Method | Why |
|---|---|---|
| Task classification (multi-label) | Weighted phrase lexicon with evidence, returns "unknown" when evidence is weak | No labelled corpus of student tasks exists. A learned text classifier trained on invented data would be fabricated evidence. The student can correct the kind of work in the screen, but corrections are not stored (the task text is never stored), so there is no data for a classifier yet. Training one would need a consented, labelled collection and is listed as future work |
| Intrinsic complexity | Deterministic scoring: category base, scope signals (deliverables, length, counts), technical cues | Explainable and testable |
| Difficulty for this student | Intrinsic complexity adjusted by the student's own skill rating, prerequisite status, resources | The only evidence available is what the student reports |
| Workload (range) | Parametric model: base effort per kind of work x scope x personal difficulty, expressed as low / likely / high | Gives honest ranges |
| Learning from history | **Statistical learning**: shrinkage estimate of the student's "actual / estimated" ratio per category, robust to outliers; preferred session length per category from completed-session rates | This is the genuine adaptive part; it needs only a few outcomes and is easy to explain |
| Scheduling | Deterministic constraint-based allocation over days (deadline, hours per day, buffer, energy) | Optimisation under constraints does not need ML; it must be reproducible |
| Ranking | Deterministic "pressure" score: remaining work vs time left, plus energy fit and wellbeing gating | Replaces deadline-only urgency |
| Wellbeing | Existing model, unchanged; only used to make the day gentler | Must not be claimed to understand tasks |
| Explanations | Templates filled from the numbers that were actually used | Every sentence is traceable to a value |

No randomness anywhere: same input gives the same output.

## 3. Pipeline

```
 text + details + answers --> [1 classify] --> kinds with evidence --+
                                                                       |
 student skill, resources ----> [2 difficulty: intrinsic + personal] --+--> [3 workload range + stages]
                                                                       |            |
 history (outcomes, sessions) ----> [4 calibrate / session prefs] -----+            v
                                                                              [5 schedule over days]
 deadline, hours per day, energy, wellbeing -------------------------------------> |
                                                                                    v
              [0 missing-information check] <------ confidence ------------- [6 explain]
                     |
        asks up to 3 questions (otherwise returns plan)
```

Modules (`backend/app/taskaware/`): `taxonomy.py`, `analysis.py`, `difficulty.py`, `workload.py`, `history.py`, `schedule.py`, `questions.py`, `explain.py`, `engine.py`, `ranking.py`, `routes.py`.

## 4. Key definitions (kept separate on purpose)

- **Total workload**: all focused minutes needed (range: low / likely / high).
- **Session duration**: one focus block, chosen per kind of work, energy and the student's history.
- **Break duration**: only after long enough sessions; none for short or administrative blocks.
- **Time until the deadline**: calendar time.
- **Available study time**: hours per day the student says they have.

## 5. Data and privacy

New tables (created automatically, no change to existing tables): `user_skills`, `task_outcomes`, `session_logs`. Only numbers and category names are stored, never task text (same rule as `recommendation_feedback`). Guests keep the same data in their browser and send a bounded summary with each request. Export and delete-account include the new tables.

## 6. Honest limits

- The classifier covers English study vocabulary only and is a lexicon, not a language model.
- Base effort numbers per kind of work are the author's design assumptions, shown as ranges; they are calibrated per student from history, not validated against a population.
- Evaluation uses scenarios written by the author and simulated students. It measures engine properties (differentiation, constraint satisfaction, calibration speed), not learning outcomes of real students. A usability study is still needed.

## 7. What was built (update 19)

**Backend** (`backend/app/taskaware/`, 12 modules). Request flow: `routes.py` validates the input (bounded text, whitelisted answer keys, 1-5 skill, history limited to 200 outcomes and 300 sessions) and calls `engine.run()`, which returns either `needs_info` (at most three questions, each with a one-line reason) or a `plan`. A plan contains: how the task was understood (kinds with the words that triggered them), generic and personal difficulty with a range, the workload as low / likely / high with stages and a method per stage, how history changed the estimate, a day-by-day schedule with the reason for each session length and break, whether it fits, what the student is unsure about, the first step, and the limits of the estimate.

**Where it plugs into the old code.** `recommend.py` ranks tasks by remaining work against time left (`ranking.py`, switch `smart_ranking` in `config.py`); the Burnout Mode filter and the wellbeing model are unchanged. `models.py` gains three tables (`user_skills`, `task_outcomes`, `session_logs`; numbers and kinds only). Account export and delete-account include them. The old `/planner/plan` topic planner is untouched.

**Endpoints:** `POST /smart/plan`, `POST /demo/smart/plan` (guest), `POST /smart/outcome`, `POST /smart/session`, `GET /smart/learned`, `PUT /smart/skills/{kind}`. See `API.md`.

**Front end.** `components/SmartPlanner.jsx` ("Plan one task" on the Study Plan page): task, optional details, deadline and hours per day; follow-up questions as choices, text or date with "Skip these questions"; the plan with difficulty (generic and for you), workload range, steps, day-by-day sessions with reasons, uncertainties; a selector to correct the kind of work; "Add to My Tasks"; and "how long did it really take" which feeds the history. `FocusTimer.jsx` can run a session picked from the plan (its own length and break, no break when the plan says none) and reports finished or abandoned sessions. Guests keep skill ratings, outcomes and sessions in the browser (`guestStore.js`) and send them with each request; on sign-up they move to the account (`importGuestData`). The old topic planner is still on the page.

**Honesty rules that are enforced in code and tests:** no randomness (same input, same output); no external AI; the plan states what it could not know; a skipped question widens the range and appears under "What I am unsure about"; history changes an estimate only after enough finished tasks of that kind (shrinkage: weight n / (n + 3)); the base effort numbers are labelled as design assumptions.

**Tests:** `backend/tests/test_taskaware.py` (45 tests: classifier, difficulty, workload scaling, history calibration and shrinkage, scheduler constraints, question gate, determinism, API validation, privacy, export and delete, ranking), `frontend/src/__tests__/smartplanner.test.jsx` (21 tests: questions, plan display, correcting the kind, add to tasks, outcome saving without the title, timer with planned sessions, guest history limits and API calls) and 5 new browser checks in `e2e/browser_e2e.py`.

**Not built:** a learned text classifier (no labelled data), a per-student learned preference screen for guests (`GET /smart/learned` works for accounts but has no screen yet), reading course material or assignment briefs, and any test with real students.
