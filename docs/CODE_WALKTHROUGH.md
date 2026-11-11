# MindSync code walkthrough (for you to explain in the viva)

Read this with the project open next to you. Each section says what the part does, which file to open, and the one-sentence reason behind the design. File names are relative to the `MindSync` folder.


## Page names (update 17: everyday English)
The page names were changed to plain words. The internal file names and web addresses are the same, so the code and tests still line up.

| Plain name shown to the student | Old technical name | Web address | File |
|---|---|---|---|
| Home | Dashboard | /dashboard | `DashboardPage.jsx` |
| My Tasks | My Tasks | /tasks | `TasksPage.jsx` |
| Study Plan | Study Planner | /planner | `PlannerPage.jsx` |
| How Are You Feeling? | Wellbeing | /wellbeing | `WellbeingPage.jsx` |
| My Progress | Analytics | /analytics | `AnalyticsPage.jsx` |
| My Settings | Settings | /settings | `SettingsPage.jsx` |
| How It Works (new, in the menu footer) | (technical text was on the Wellbeing page) | /how-it-works | `HowItWorksPage.jsx` |

"Burnout Mode" is shown to the student as **Gentle Mode** ("Taking it easy today"). The code, the API and the report still call it Burnout Mode.

## 0. The big picture in one minute

```
 Browser (React)  <--HTTPS/JSON + JWT-->  FastAPI backend  <--SQL-->  PostgreSQL
                                              |
                                   loads JSON model files (plain numbers)
                                   written earlier by the training scripts
```
* **Frontend** shows pages and sends requests. It never decides anything important; it only displays what the backend returns.
* **Backend** checks who you are, validates the input, reads or writes the database, runs the ranking and the models, and returns JSON.
* **Database** stores users, tasks, energy check-ins, wellbeing results and "was this helpful" answers.
* **Models** are trained offline (`backend/ml_training/`), saved as small JSON files (`backend/app/ml/*.json`), and loaded by the backend at start-up. No outside AI is called anywhere.

## 1. Follow one request: "show me my recommendation"

1. `frontend/src/context/AppDataContext.jsx` (used by `DashboardPage.jsx`) calls `dataApi.recommend()`.
2. `frontend/src/dataApi.js` picks the account version (`createUserApi`) or the guest version (`createGuestApi`). Same screen, two data sources.
3. `frontend/src/api.js` `request()` adds the JWT header and calls `GET /recommend`.
4. `backend/app/main.py` sends it to `backend/app/recommend.py`. The security middleware adds headers on the way out.
5. `get_current_user` (`backend/app/auth.py`) decodes the JWT; no valid token means HTTP 401.
6. `recommend()` reads **only this user's** pending tasks and last five energy check-ins, and asks `latest_recent_label()` (`wellbeing.py`) if a fresh "High" wellbeing result exists.
7. `build_recommendation()` calls `rank_tasks()` in `heuristic.py` (score = 0.6 x deadline urgency + 0.4 x energy match; hides hard tasks in Burnout Mode), then `explain_recommendation()` in `explain.py` writes the sentence.
8. FastAPI turns the Pydantic object (`RecommendationOut` in `schemas.py`) into JSON; React draws `RecommendationCard.jsx`.

*Why `build_recommendation` is a plain function:* the guest route (`demo.py`) uses exactly the same code, so the ranking logic exists once.

## 2. Backend, file by file

| File | What it does | Why it is built this way |
|---|---|---|
| `config.py` | Reads settings (`.env`) such as database URL and JWT secret | Secrets live outside the code; nothing hard-coded |
| `database.py` | Async database connection, `get_db`, small start-up migrations | Async keeps the API fast under many requests |
| `models.py` | The tables as Python classes (`User`, `Task`, `EnergyCheckin`, `WellbeingCheck`, `RecommendationFeedback`) with CHECK constraints and foreign keys | The database itself refuses bad data, even if the API had a bug |
| `schemas.py` | Pydantic classes that validate every request and shape every response | First validation layer (types, ranges, lengths) |
| `security.py` | Argon2id password hashing and JWT creation/decoding | OWASP-recommended; slow on purpose so guessing is expensive |
| `auth.py` | Register, login, `/auth/me`, the `get_current_user` dependency | Login does a hash check even for unknown emails so timing does not reveal who is registered |
| `ratelimit.py` | Sliding-window limiter used for login, sign-up, guest routes, wellbeing and feedback | Stops brute force and spam; counters live in memory (limitation noted) |
| `tasks.py`, `energy.py` | CRUD for tasks and energy check-ins | Every query filters by the logged-in user's id, so other users' data returns 404 |
| `heuristic.py` | Pure ranking functions | Pure = no database or network, so it is fast and easy to test |
| `explain.py` | Builds the explanation text from the scores | Deterministic: every sentence comes from a number, nothing invented |
| `ml/features.py`, `ml/predictor.py` | Experimental task-fit model (logistic regression, off by default) | Trained on simulated data, so it only affects ranking if `ML_ENABLED=true` |
| `ml/wellbeing_model.py` | Loads the wellbeing JSON; validates answers; predicts; explains | No scikit-learn at run time; strict validation is a security layer |
| `wellbeing.py` | Wellbeing routes, 14-day validity, rate limit | Only the latest recent result affects Burnout Mode |
| `planner.py` | Study planner: rates topics (rules) and builds timed blocks | A rule-based planner is honest and explainable |
| `feedback.py` | Stores "was this helpful?" answers (numbers only) | The project's real-world evaluation data |
| `account.py` | Export my data, erase wellbeing history, delete account | Privacy rights; deletion needs the password again |
| `notifier.py`, `notifications.py` | Email alert 48 h before a deadline (background loop) | One email per task; SMTP or a local outbox folder |
| `demo.py` | Stateless guest routes | Guests keep data in their browser; the server stores nothing |
| `modelcards.py` | Public model facts (`/models/status`) | Evidence for "How the models work" |
| `main.py` | Builds the app, CORS, security headers, registers routers | Narrow CORS (one origin) and defensive headers (OWASP A05) |

### 2b. The task-aware engine (`backend/app/taskaware/`, update 19)

| File | Role |
|---|---|
| `taxonomy.py` | The kinds of work (programming, maths, writing, exam, reading, presentation, data, admin, general), their trigger phrases and weights, base effort per stage and the study method for each stage |
| `analysis.py` | Reads the text: which kinds (noisy-or of the matched phrase weights), counts such as words, pages, problems, slides, size cues, deliverables |
| `difficulty.py` | Generic difficulty from scope and kind; difficulty for this student from skill rating, prerequisites and resources; returns a range |
| `workload.py` | Minutes per stage as low / likely / high; removes the part already finished |
| `history.py` | Learns from finished tasks: per-kind ratio (actual / estimated), shrunk towards 1 with weight n / (n + 3), outliers capped; preferred session length per kind from logged sessions |
| `schedule.py` | Puts the stages on the days left: even pace with a buffer, daily minutes, deep-work limit, review on a later day, breaks only after long enough sessions |
| `questions.py` | Decides what is missing and asks at most three questions, never the same one twice |
| `explain.py` | Sentences built from the numbers actually used |
| `engine.py` | Runs the steps in order and returns `needs_info` or `plan` |
| `ranking.py` | Task ranking by remaining work against time left |
| `routes.py` | HTTP endpoints and input validation |

Viva answer in one line: *"The estimate is a transparent formula plus a per-student correction learned from their own finished tasks; the only machine learning is that statistical correction, because there is no labelled data to train a text model honestly."*

## 3. Database design

Five tables (see `docs/diagrams/erd.png`): `users` (1) -> (many) `tasks`, `energy_checkins`, `wellbeing_checks`, `recommendation_feedback`. Foreign keys use `ON DELETE CASCADE`, so deleting a user removes their rows.
Two validation layers: Pydantic in the API **and** CHECK constraints in the database (difficulty 1-5, energy 1-5, risk label Low/Medium/High). `wellbeing_checks.answers` and `probabilities` are JSON columns, because the questionnaire comes from the model file and can change without a schema change. `tasks.completed_at` is set when a task is marked done; it powers the progress charts.

## 4. The machine-learning pipeline

**Wellbeing model (the real model).** File: `backend/ml_training/wellbeing_train.py`. Steps, in the order the script prints them:
1. Load and check the survey CSV (missing values, duplicates, class balance).
2. Choose only habits a student can change; leave out age, gender, university type, tuition, family income.
3. Never use `Stress_Score` (the label was computed from it: that would be label leakage). The script measures what happens if it is included, to prove the point.
4. Split 60 / 20 / 20 (train / validation / test), stratified, fixed seed 42.
5. Fit the scaler on the training part only (no leakage), one-hot encode text answers.
6. Compare algorithms on the validation set: majority-class guess, decision tree, random forest, gradient boosting, logistic regression with several regularisation strengths.
7. Refit the chosen logistic regression on train + validation; evaluate once on the test set: accuracy, macro-F1, precision / recall / F1 per class, confusion matrix, log-loss, ROC-AUC, 95 % bootstrap intervals, 5-fold cross-validation.
8. Calibration: do predicted probabilities match how often the model is right (expected calibration error, reliability table)?
9. Check how rule-made the dataset's score is (can a linear formula rebuild it? do the classes equal score cut-offs?).
10. Export scaler, coefficients, questionnaire, metrics and limitations to `app/ml/wellbeing_weights.json`.

At run time `app/ml/wellbeing_model.py` does: validate answers -> one-hot encode -> standardise with the saved mean/scale -> one linear score per class -> softmax -> probabilities. For the explanation it takes, per question, `(weight_High - weight_Low) x standardised answer`; the biggest positive numbers are "what is raising your risk".

**Task-fit model (experimental).** `ml_training/train.py` trains on 20,000 **simulated** rows (`synth_data.py`) with the same split discipline and exports `model_weights.json`. It is off by default because simulated labels encode our own assumptions; the ranking is the transparent formula.

**Why logistic regression:** explainable (one weight per answer), performs about as well as trees/boosting on this table (the trainer shows the comparison), tiny to store and fast to run.

## 5. Frontend

| File | Role |
|---|---|
| `main.jsx`, `App.jsx` | Starts React and defines the routes: public pages (`/`, `/login`, `/register`, `/forgot-password`, `/reset-password`) and the six app pages inside one frame (`/dashboard`, `/tasks`, `/planner`, `/wellbeing`, `/analytics`, `/settings`) |
| `context/AuthContext.jsx` | Keeps the JWT (localStorage) and the current user |
| `api.js` | One `request()` helper: adds the token, turns server errors into plain English, explains "cannot reach the server" |
| `dataApi.js` | One interface with two back-ends: account (server) and guest (browser) |
| `guest/guestStore.js` | The guest's data in localStorage; mirrors server rules (`completed_at`, 14-day wellbeing window) |
| `components/AppShell.jsx` | The frame around every app page: left menu (a slide-in drawer on phones), header, banners and the page itself (`<Outlet/>`) |
| `context/AppDataContext.jsx` | Loads the tasks, check-ins and recommendation ONCE and shares them with all pages; every create/complete/edit/delete goes through it so all pages stay in step |
| `pages/DashboardPage.jsx` | "Home": a welcome card for new students, then one suggested task ("Do this first"), the energy buttons, what is due today, the next deadline and this week's progress |
| `pages/TasksPage.jsx` | Add, edit, complete, delete, search, filter and sort tasks; task details |
| `pages/PlannerPage.jsx` | "Study Plan": how busy you are, the plan maker and the study timer (planner photo) |
| `pages/WellbeingPage.jsx` | "How Are You Feeling?": the eight-question check, the result, "Make My Plan Easier" and a "can and cannot do" card. The technical model description lives on How It Works |
| `pages/AnalyticsPage.jsx` | "My Progress": tasks finished, days in a row, 4-week chart, energy, by subject and difficulty, "What we noticed" |
| `pages/SettingsPage.jsx` | "My Settings": about you, email reminders, change password, download or delete data |
| `pages/HowItWorksPage.jsx` | "How It Works": plain explanation of the ranking, Gentle Mode, the stress-level check (and what it cannot do), the study plan, privacy, photo note, and the technical model details (`ModelInfo`) |
| `friendly.js` | Everyday-English helpers: "due tomorrow at 18:00", the one-sentence reason for a task, Gentle Mode wording (unit-tested). The reason only restates numbers the server already calculated |
| `components/Photo.jsx`, `components/PageHeader.jsx`, `components/AuthPhoto.jsx` | A responsive WebP photo with alt text and a focus point; the page top (a photo banner on four pages) with title, purpose and a "Start here" line; the photo beside the log-in and sign-up forms |
| `components/*` | `SmartPlanner` (one-task planner, update 19), `TaskForm`, `TaskList` (priority order, edit), `RecommendationCard` (why + feedback), `WellbeingCheck` (form generated from the model's questions), `ProgressPanel`, `StudyPlanner`, `AccountPanel`, `ModelInfo`, `AlertSettings`, `FocusTimer`, `EnergyCheckinWidget`, `EnergyHistory` |
| `progress.js` | Pure functions for the statistics (unit-tested) |
| `pages/LandingPage.jsx` | Welcome page: "Study Smarter. Feel Better.", full-width hero photo with a dark-blue gradient, four benefits, three steps, a photo band, short questions, photo credits |

*Why the wellbeing form is generated:* the questions, ranges and options come from the model file, so the form, the validation and the model can never disagree.

## 6. Security architecture (OWASP Top 10 mapping)

| Risk | What MindSync does | Where |
|---|---|---|
| A01 Broken access control | Every query filtered by the token's user id; 404 for other users' ids; account deletion needs password | `tasks.py`, `account.py` |
| A02 Cryptographic failures | Argon2id hashes; JWT signed with a server secret; no secrets in code | `security.py`, `config.py` |
| A03 Injection | Parameterised queries (SQLAlchemy); Pydantic validation; strict wellbeing answer validation; React escapes output | `schemas.py`, `wellbeing_model.py` |
| A04 Insecure design | Rate limits; DB CHECK constraints; server decides Burnout Mode | `ratelimit.py`, `models.py` |
| A05 Misconfiguration | Narrow CORS; security headers; generic error messages | `main.py` |
| A07 Authentication failures | Lock-out after 5 failed logins; password rules; timing-safe login | `auth.py` |
| A09 Logging | The app logs failures without passwords or tokens | `main.py` |
| Privacy | Guests keep data in the browser; export and erase tools; no outside AI | `account.py`, `guestStore.js` |

Tests that prove these: `backend/tests/test_security_hardening.py`, `test_api_integration.py`, `scripts/security_probe.py` (live attack script).

## 7. How the tests are organised

| Layer | Tool | Where |
|---|---|---|
| Backend unit + integration + database | pytest, in-memory SQLite database | `backend/tests/` |
| Model pipeline | pytest, trains on a synthetic stand-in CSV (never shipped) | `tests/test_wellbeing.py`, `tests/standin.py` |
| Frontend unit/component | vitest + Testing Library | `frontend/src/__tests__/` |
| End-to-end browser | Playwright driving the real pages and API | `e2e/browser_e2e.py` |
| Live security attack | httpx script against the running API | `backend/scripts/security_probe.py` |
| Performance | latency script, per endpoint and concurrent | `backend/scripts/benchmark_latency.py` |

## 8. Questions you can now answer
* "Where does the explanation come from?" `explain.py`, built from the scores, no AI.
* "What stops user B reading user A's tasks?" the `owner_id` filter and the 404 in `tasks.py`.
* "How does a prediction get made?" section 4, last paragraph.
* "What happens if the model file is missing?" `MODEL is None`: the route returns 503 and the screen hides the check.

## 9. Where the update 24-25 features live (My Tasks, reminders, Studio, Profile)

| Question | File |
|---|---|
| Where is the whole roadmap saved? | `backend/app/assist/store.py` (`store_plan` keeps history), table `plan_sessions` in `models.py`; schema in `database/schema.sql` |
| How is the My Tasks screen worked out? | `backend/app/assist/roadmap_view.py` (one pure function, shared by signed-in students and guests) |
| What happens when I press Done? | `backend/app/assist/roadmap.py` (`confirm`) which reuses `log_session` in `routes.py`, so the learning record, the Dashboard and the roadmap stay in step |
| How does a new plan keep my history? | `store_plan` (finished blocks stay, only future planned blocks are replaced) and `/roadmap/replan/preview` then `/apply` with `confirm: true` |
| How are reminders made without duplicates? | `backend/app/assist/reminders.py` (`compute` is a pure function; `sync` stores one row per key, unique per student) |
| How is a quiz marked without AI? | `backend/app/studio/routes.py` (`submit_quiz`): compares the choice with the stored answer |
| How does spaced revision work? | `backend/app/studio/srs.py` (boxes 0-5, waiting 0, 1, 3, 7, 14, 30 days) |
| Where is the AI called? | only `backend/app/studio/pack.py` (`generate`), through `backend/app/ai/provider.py`; guards and limits sit in front of it |
| How is AI switched on or off? | `AI_PROVIDER` in `backend/.env` (`provider.build_provider`); off by default |
| Guest versions of all this | `frontend/src/guest/guestRoadmap.js`, `guestStudio.js`, `guestStore.js` (browser storage, same rules) |
| Themes, larger text, contrast | CSS variables in `frontend/src/styles.css`, applied in `context/AppDataContext.jsx` |
| Profile, password, e-mail change, delete account | `pages/ProfilePage.jsx`, `components/AccountPanel.jsx`, `backend/app/account.py` |

New tests: `backend/tests/test_roadmap.py`, `test_studio.py`, `test_studio_helpers.py`, `test_profile_account.py`; `frontend/src/__tests__/guestRoadmap.test.js`, `guestStudio.test.js`, `dayLabels.test.js`, `pages.test.jsx`, `components.test.jsx`; browser: `e2e/browser_e2e_seven_pages.py`.
