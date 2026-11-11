# MindSync - presentation and viva guide

Written in simple English so you can say it in your own words. The model numbers and test results below were all produced by running the code (see `docs/CHAPTER4_EVIDENCE.md`). Items still marked **[FILL]** need something only you can supply (usability test, speed re-run). Never say a number you have not seen on your own screen.

---

## Part 1 - Presentation outline (about 10-12 minutes)

### 1. Title and objective
**MindSync: an energy-aware study planner that helps students avoid burnout.**
Objective: help a student decide *what to study next*, based on deadlines, how hard the task is, and how much energy they have, and warn when their habits point to high stress.

### 2. Problem statement
Students have many deadlines. Most to-do apps sort only by date. They ignore that a very hard task at low energy leads to stress, procrastination and burnout.

### 3. Target users
University students (especially in their final years) who manage coursework, projects and exams with limited time.

### 4. Existing problem vs our solution
| Normal to-do app | MindSync |
|---|---|
| Sorts by date | Scores urgency AND difficulty-vs-energy |
| Ignores how you feel | Energy check-in, Burnout Mode |
| No insight into habits | Wellbeing check from a model trained on real student survey data |
| Cloud AI or nothing | Own models, run locally, no outside AI |

### 5. Main features
Task ranking with an explanation (priority numbers 1, 2, 3 ... come from the formula, not typed in by the student); editable tasks; energy check-in and Burnout Mode (the screen says why it is on and how to turn it off); Wellbeing check (trained model); study planner (focus/break blocks); progress panel (completed this week, 7-day streak, on-time rate); "Was this helpful?" feedback; account page (download my data, erase wellbeing results, delete account); email alert 2 days before a deadline; guest mode (try without an account).

### 6. Technologies and why
- **React + Vite**: fast, component-based screens.
- **FastAPI (Python)**: quick, automatic validation and API docs, same language as the machine-learning code.
- **PostgreSQL**: reliable relational database with constraints.
- **Argon2id + JWT**: modern password hashing; stateless login tokens.
- **scikit-learn (training only)**: standard ML library; the app itself uses small plain-Python code to run the saved model.

### 7. Architecture
Show `docs/diagrams/architecture.png`. Say: *Browser (React) -> API (FastAPI) -> database. The models are files of numbers (JSON) that the API loads at start-up. Nothing goes to an outside AI service.*
Data flow of one recommendation: browser sends the JWT -> API finds the user -> reads that user's pending tasks and latest energy -> formula + task-fit model score each task -> `explain.py` writes the sentences -> JSON back to the browser.

### 8. Database design
Show `docs/diagrams/erd.png`. Five tables: `users`, `tasks` (with `completed_at` for the progress panel), `energy_checkins`, `wellbeing_checks`, `recommendation_feedback` (helpful yes/no plus the energy, difficulty and hours-left at that moment; no task text). Every child row points to its user (foreign key, delete cascades). Database CHECK constraints (difficulty 1-5, energy 1-5, risk label Low/Medium/High) repeat the validation the API already does: two layers.

### 9. AI model architecture
Two small models, both **logistic regression** (a model that adds up weighted evidence and turns it into a probability).
1. **Wellbeing model (trained on a public dataset):** 8 answers -> confidence for a Low / Medium / High stress level. Multinomial logistic regression. Each answer has a weight per class, so we can say *which answers raised your estimate*.
2. **Task-fit model (simulated data, prototype):** 6 numbers about a task and the student's energy -> probability the task is a good fit now. **Experimental and switched off by default**, because its data is simulated; the ranking uses the transparent formula only. Say this openly: it is an honest design decision, not a missing feature.
Say clearly: the task-fit model is trained on simulated data, so its scores show the pipeline works, not real-world accuracy.

### 10. Dataset and preprocessing (wellbeing model)
University Student Stress Dataset, Mendeley Data, DOI 10.17632/rc5htd5dfr.1, CC BY 4.0: 3,000 rows described as responses of undergraduates in Bangladesh (not DMU students); 3,000 rows used after cleaning (no missing values, no duplicates).
Steps: remove incomplete rows -> keep only habits the student can change -> exclude age, gender, university type, tuition, family income (fairness) -> exclude `Stress_Score` (the label comes from it - using it would be cheating) -> drop questions that carry no information (study hours, class attendance, peer pressure: zero effect on the label) -> standardise numbers with a scaler fitted on the training part only.
**Key finding to present:** the dataset's stress score is an exact formula of the answers (R squared = 1.0), the levels are just cut-offs of it, and the columns look randomly generated (all flat, no correlations above 0.041). So the model recovers a scoring rule; it does not measure real stress.

### 11. Training and evaluation
Split 60% train / 20% validation / 20% test (stratified, fixed seed). Validation is used to choose settings. The test set is used **once**, at the end. Metrics: accuracy, macro-F1, ROC-AUC, confusion matrix, and the **majority-class baseline** (what you get by always guessing the most common answer). Also 5-fold cross-validation and a comparison with tree/forest/boosting models.
**Results (600 untouched test students):** accuracy 0.9967, macro-F1 0.9936, ROC-AUC 1.0, log-loss 0.0858; always-guess baseline accuracy 0.4767 (macro-F1 0.2152); 5-fold cross-validation macro-F1 0.9952 (std 0.0039); 95% interval for accuracy 0.9917-1.0000. Random forest 0.8517 and gradient boosting 0.8767 do worse because the rule is linear. 2 mistakes in 600, both High students rated Medium.
Say what the numbers mean: a model is only useful if it beats the baseline. Also say what the percentage means: it is the model's estimate of how often students with those answers were labelled in that class **in this dataset**. It is not the chance that *you* will burn out. The score-structure check shows exactly that: the label is a straight formula of the answers, so the model has learned the dataset authors' scoring rule. Say it as a limit, not a hidden fact. Calibration: expected calibration error 0.073, Brier 0.038; the model is slightly under-confident (predictions at about 70% confidence were right every time), so the percentages are cautious.

### 12. Important source code (show 3 short pieces)
1. The ranking formula, `backend/app/heuristic.py`: `score = 0.6 * deadline_urgency + 0.4 * energy_match`.
2. The wellbeing prediction, `backend/app/ml/wellbeing_model.py` `predict()`: standardise -> one linear score per class -> softmax -> probabilities.
3. The training script, `backend/ml_training/wellbeing_train.py`: the numbered steps with comments.

### 13. Security and privacy
Argon2id hashing; JWT with expiry; every query filtered by the logged-in user (other users' data returns 404, not 403); Pydantic + database constraints; login lock-out after 5 failures; rate limits on guest routes; strict validation of model inputs (unknown keys, out-of-range values, text instead of numbers are rejected); CORS limited to one origin; security headers; no secrets in code. Privacy: guests' data stays in their browser; no data sent to outside AI; demographic data not collected by the wellbeing check.

### 14. Testing results (real numbers only; all run on 21 Oct 2026)
**On my laptop (Windows, local PostgreSQL), the target environment:**
- Backend tests (`run-tests.bat`): **143 passed, 0 failed**. Frontend tests: **34 passed**.
- Live security probe with the real wellbeing model (`run-security-test.bat`): **51 / 51** checks passed (SQL injection, XSS, forged tokens, access control, brute force, input validation and more).
- Full browser test in real Chrome (`run-e2e.bat`): **30 / 30** (guest journey, Burnout Mode, wellbeing result, planner, sign-up, add/edit/complete tasks, progress, feedback, export, account deletion).
- Speed (`run-benchmark.bat`, target: 95% of requests under 3,000 ms): one user, 20 tasks, 50 requests: `/recommend` median 91-117 ms (p95 153-189 ms), `/tasks` median 60-73 ms, planner median 46-64 ms, wellbeing result median 75-88 ms. **10 students at once, 100 requests, two runs: 100 / 100 succeeded, p95 2,948 ms and 1,663 ms, median 1,476 ms and 933 ms, slowest single request 4.3 s and 3.0 s.** So the target is met, but narrowly in the first run.
**Honest story about speed (say this, it shows engineering):** the first run on my laptop failed (median 1.95 s, p95 12.8 s, 3 of 100 requests timed out). I measured the database separately: a new PostgreSQL connection took about 360 ms on Windows and the laptop had only 0.37 GB of 7.7 GB memory free. Fixes: connections opened in advance, and password hashing moved off the main loop. After the fixes: no timeouts. Limits: the laptop is memory-starved (a single request takes about 100 ms here but about 6 ms on a Linux machine), so a production server would be faster; I did not test more than 10 simultaneous users.
**Build environment (Linux, not the target):** the same 143 + 34 tests, 30 / 30 browser test, 51 / 51 security.
**Model evaluation:** reproduced three times with identical numbers (accuracy 0.9967, macro-F1 0.9936), including by `train-wellbeing.bat` on my laptop.
**Problems the tests found and I fixed (good viva material):** no tab icon caused a console error in Chrome (added one); the first browser test was too impatient for a slow laptop (now waits properly); the 10-user speed failure above.
- **Usability test:** **[FILL: SUS score and number of participants, or say "not done yet"]**.
- **Not tested:** the wellbeing model on real DMU / Niels Brock students; more than 10 simultaneous users; real email delivery. The backend unit/integration tests use an in-memory SQLite database; PostgreSQL itself is exercised by the security probe, the benchmark and the browser test.

### 15. Limitations and future work
Limitations: one public survey, self-reported answers, correlation not causation; the label is a survey stress score, not a clinical assessment; the task-fit model uses simulated data; rate limiter lives in memory; token stored in localStorage.
Future work: log completed/abandoned sessions and retrain the task-fit model on real data; collect consent-based feedback to validate the wellbeing model; httpOnly cookie; Redis for rate limits; mobile app.

### 16. Live demo plan (5 minutes, rehearse twice)
Start backend and frontend first. Have the app open on the landing page.
1. Landing page -> **Try it now (guest)**. Say: no account needed; data stays in the browser.
2. On **Home**, press **Show me with example tasks**. Show "Do this first" and its one-sentence reason. Say: Home is only a summary; each feature has its own page in the left menu, in everyday words.
3. Press energy **5**, then **1**. Gentle Mode ("Taking it easy today") turns on; hard tasks disappear. Say why. Open **My Tasks**: show the priority numbers, search, filters and a task's Details.
4. Open **How Are You Feeling?** -> the check is already open. Set a stressful week (many study hours, little sleep, high anxiety) -> **Show my result**. Show the probability bars, the "what is raising your estimate" list and the "What this check can and cannot tell you" card. Say: *this is a model trained by me, not ChatGPT*. A High result turns Burnout Mode on and the page shows the matching workload adjustment.
5. On the same page open **How the models work**. Show the real metrics and the limitations.
6. **Study Plan**: type "Python basics, SQL joins, Machine learning", press **Make my plan**; drag a slider; show the plan changes; show the study timer below it. Then **My Progress** (empty for a guest: say that it fills in as tasks are finished).
7. Click **Create account**, register; guest data moves into the account. Open **My Settings** and show the email-reminder switch. Finally open **How It Works** and say that all the technical detail is kept there.
8. Show pgAdmin: `users.password_hash` is an Argon2id string; `wellbeing_checks` has your result.
9. Show `run-tests.bat` and `docs/security_test_results.md` in the terminal.
Backup plan: if the wellbeing check does not appear, the weights file is missing - say so honestly and show the training script and metrics file.

---

## Part 2 - Viva questions and answers (38)

**1. What problem does MindSync solve?**
Students rank tasks by date only. MindSync also considers difficulty and energy, and warns about stress, so they work on the right thing at the right time and avoid burnout.

**2. Why not just use ChatGPT or another cloud AI?**
Cost, privacy, dependency and explainability. Every request would send student data outside, need an API key and internet, and the answers could not be tested. My own small models run locally, are fast, are free, and I can show exactly how they were trained and scored.

**3. How does the ranking work?**
Score = 0.6 x deadline urgency + 0.4 x energy match. Urgency is 1 if overdue or due within 24 h, otherwise it falls as the deadline gets further away. Energy match is 1 minus the gap between task difficulty and energy, divided by 4. The experimental task-fit model is off by default, so the score is exactly this formula.

**4. Why those weights, 0.6 and 0.4?**
They are a judgement: missing a deadline is worse than a poor match. They are settings, and with real usage data they could be tuned.

**5. What is Burnout Mode?**
When the latest energy is 1 or 2, or the latest wellbeing result (within 14 days) is High, tasks harder than level 2 are hidden. The model cannot override it. Trade-off: one low reading triggers it; I chose that for usability and noted that smoothing over several readings would be more robust.

**6. What is logistic regression, in simple words?**
It multiplies each input by a weight, adds them up, and turns the total into a probability between 0 and 1. For three classes (multinomial) it makes one total per class and normalises them (softmax) so they add to 100%.

**7. Why logistic regression and not a neural network?**
Similar accuracy on this small table, much easier to explain (each answer has a weight), tiny to run, and it can be exported as JSON. The trainer compares trees, forests and boosting to check I am not losing accuracy.

**8. Which dataset did you use and is it legitimate?**
The University Student Stress Dataset on Mendeley Data, DOI 10.17632/rc5htd5dfr.1, licence CC BY 4.0, cited in the report. It is a survey of university students.

**9. What is label leakage and did you avoid it?**
Leakage is when a feature contains the answer. The Low/Medium/High label comes from `Stress_Score`, so using it as an input gives an almost perfect but useless model. I excluded it, and the trainer prints what the score would have been with it, to prove the point.

**10. Why did you exclude age, gender and family income?**
Fairness and usefulness. A stress estimate should not depend on who someone is, and the student cannot change those things, so they would give no helpful advice.

**11. How did you split the data and why three parts?**
60% train, 20% validation, 20% test, stratified so each part has the same class mix. Train teaches the model, validation chooses settings, and the test set is used once at the end so the result is honest.

**12. What do accuracy, macro-F1 and ROC-AUC mean?** 
Accuracy: share of correct answers. Macro-F1: average F1 of the three classes, so a rare class counts equally. ROC-AUC: how well the model ranks a true "High" above a true "Low" (0.5 = coin flip, 1.0 = perfect).

**13. Is your accuracy good?**
On the test set it scores 99.7% against a 47.7% always-guess baseline, and cross-validation agrees (macro-F1 0.995). But I must be clear about what that means: the dataset's label is a formula of the answers, so a high score shows the model recovered that formula, not that it can predict real stress. I would not claim more than that, and the app says so.

**14. The task-fit model uses simulated data. Is that valid?**
It is a prototype and the app says so. The data comes from stated assumptions, so the model learns my assumptions, not real behaviour. The scores prove the pipeline (data -> train -> evaluate -> deploy -> serve) works. With real logged sessions I would retrain.

**15. How do you explain a wellbeing result to the user?**
For each answer I compute (weight for High minus weight for Low) x the standardised answer. Positive means that answer pushes towards High. The top three up and down are shown with a tip.

**16. Is this a medical diagnosis?**
No. It is a study-habit screening aid trained on survey data. The app says so on every result and suggests talking to someone or student support. I do not store any health diagnosis, only the habit answers and the predicted label.

**17. What if the model is unsure?**
The result page shows the confidence and the full probability bars. A 45/40/15 split looks different from 90/8/2. Limitations are shown in "How the models work".

**18. How is the app protected against bad input?**
Pydantic checks types, lengths and ranges; the wellbeing route also rejects unknown keys, numbers outside the trained range, text where a number is needed; the database has CHECK constraints; queries are parameterised (no SQL injection).

**19. Why Argon2id?**
It is the OWASP-recommended password hash. It is memory-hard, so GPUs cannot test billions of guesses cheaply. Plain hashes like SHA-256 are far too fast; bcrypt is acceptable but older.

**20. What if a JWT is stolen?**
It expires after 60 minutes. It is kept in localStorage, which a cross-site-scripting bug could read; an httpOnly cookie with CSRF protection would be stronger (future work).

**21. How do you stop one user reading another's data?**
Every query filters by the user id from the verified token, never from the request. Someone else's task id returns 404, so it does not even reveal that the task exists. This is tested (integration tests and the live probe).

**22. How do you know the system works? What did you test?**
On my laptop, in the real environment: 143 backend tests and 34 frontend tests passed; a live security probe that attacks the running API (SQL injection, XSS, forged tokens, brute force, bad inputs) passed 51 / 51; and a test that drives real Chrome through the whole app passed 30 / 30. The model was retrained three times with identical results. A speed test with 10 simultaneous users first failed, so I diagnosed and fixed it (question 37), and it now passes.

**23. What did the tests NOT cover?**
Real-world accuracy of the wellbeing model, more than 10 simultaneous users, real email delivery, and a usability test with real students (unless done). The unit tests use in-memory SQLite, not PostgreSQL.

**24. Does it work without internet?**
The app runs on my own server and needs no outside service. Both models are local files. (Email alerts need SMTP to send; without it they go to a local outbox.)

**25. What would you do differently?**
Collect real usage data earlier, run the usability test sooner, smooth the Burnout Mode trigger, and validate the wellbeing model with consenting students.

**26. What did you learn?**
Prepare three honest sentences: for example, that a high score can be fake (label leakage), that honest baselines matter, and that removing features made the project clearer.

**27. What was your own contribution versus libraries?**
The data preparation choices, the training and evaluation design, the explanation method, the API and database design, the tests and the security checks. Libraries I used: FastAPI, SQLAlchemy, scikit-learn, React. I trained the models myself; I did not use any pre-trained model.

**28. Priorities are 1, 2, 3 and the student cannot type them. Why?**
A typed priority goes stale and every student marks everything "high". Here the order comes from the deadline and the student's energy today, so it changes when their situation changes, and the card explains why. The student keeps control: they can still edit the deadline and the difficulty.

**29. How do you evaluate whether the recommendations are any good?**
Students can answer "Was this helpful?" under each recommendation. I store yes/no with the energy, difficulty and hours left (no task text) and show the helpful percentage in the progress panel. That is a real-world measure, but with a small number of users it is only indicative; I report the number of answers next to the percentage. **[FILL: your usability-test numbers]**

**30. Why is the task-fit model switched off?**
It was trained on simulated data, so it learned my assumptions rather than real student behaviour. A transparent formula is more honest. I kept it to show the full pipeline and it can be switched on with one setting. If real feedback accumulates, the feedback table is the starting point for a model trained on real labels.

**31. Does your wellbeing percentage predict real burnout?**
No. It estimates the label the dataset's authors derived from survey answers, for Bangladeshi students. It is a screening aid for reflection, not a diagnosis, and the app says so on every result.

**32. What can a user do with their own data?**
Download everything as JSON (never the password hash), erase wellbeing results, or delete the account with their password. Deletion removes all their rows (cascade). This is tested.

**33. Your model scores about 99.7%. Is it really that good?**
It is accurate at what it was trained to do, which is to reproduce the dataset's scoring rule. I checked and found the stress score is an exact formula of the answers (R squared 1.0), and the three levels are cut-offs of it. So high accuracy is expected and is not evidence about real students. Tree-based models, which cannot copy a linear rule exactly, score about 0.81 macro-F1 on the same data. I report this openly.

**34. Why does MindSync ask only 8 questions when the dataset has 11 habit columns?**
I tested each question by removing it and measuring validation log-loss. Study hours, class attendance and peer pressure changed nothing (the dataset's score gives them zero weight), so asking students for them would be pointless. The other 8 each made the model clearly worse when removed.

**35. Is the dataset real?**
It is described as a survey of Bangladeshi undergraduates, and I use it under its CC BY 4.0 licence with citation. But its statistics are unusual for a real survey: every column is flat (uniform) and no two inputs correlate by more than 0.041, and the score is an exact formula. That is consistent with generated data. I cannot prove it, so I say that I treat it as a dataset for demonstrating the machine-learning pipeline and would need real student data to make any claim about real stress.

**36. What does the percentage on the result mean?**
How confident the model is that the dataset's scoring rule would put your answers in that band. Calibration on the test set: error 0.073, and the model is slightly under-confident. It is not the chance of burnout.

**37. Did your performance test pass? What went wrong?**
It failed the first time. One user was fast (50-100 ms), but with 10 students at once some requests timed out. I measured the database alone: on my Windows laptop opening a new PostgreSQL connection took about 360 ms (7 ms on Linux), and the laptop had only 0.37 GB of 7.7 GB memory free. The app opened connections only when needed, so students arriving together each waited. Fix 1: open a pool of connections at start-up (p95 for 10 parallel database queries went from 449 ms to 97 ms). Fix 2: password hashing is deliberately slow and was freezing the whole server while it ran; it now runs on worker threads (a test proves the server stays responsive). Result on the laptop, two runs: 100 / 100 requests succeeded, p95 2.9 s and 1.7 s, against a 3 s target. The margin was narrow in the first run, and I say so.

**38. How do you debug a problem on a computer you cannot see the console of?**
The backend writes a small private error log (`backend/logs/backend_errors.log`) with the error type and the code lines where it happened, but never the message, e-mail or password. It showed within a minute that a failing sign-up was `ConnectionRefusedError`: the PostgreSQL service was not running, not a bug in my code.

---

## Part 3 - Things to say if you are asked "show me"
- Training from scratch: `python -m ml_training.wellbeing_train --csv data/<file>.csv` prints every step.
- The saved model: open `backend/app/ml/wellbeing_weights.json` (numbers only).
- Proof of no outside AI: search the backend for `import openai`, `google.generativeai` or `anthropic`, or any call to an outside AI address: there are none; `GET /models/status` returns `external_ai_used: false`.
