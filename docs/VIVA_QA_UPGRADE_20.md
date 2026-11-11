# Viva questions for update 20 (short answers, true to the code)

**What is new compared with the earlier version?** One connected planner instead of two separate ones. You describe tasks in your own words; MindSync checks them against everything already planned; you see one report with a verdict and verified alternatives; you accept; you study with a timer tied to each block; your feedback changes later estimates. See `UPGRADE_20_EVALUATION.md`, section 2, for a same-input comparison.

**Where is the AI, and what does it do?** An optional external language model (OpenAI) reads free text, writes explanations, answers questions and words the weekly review. It does no calculation. Everything with numbers (workload, schedule, feasibility, alternatives) is deterministic Python. Without a key the app still works on rules and says so on screen.

**Did you train the language model?** No. It is pretrained and external. What I trained locally is the stress-level model (logistic regression on a public survey dataset). The personal difficulty and time estimates are rules fed by the student's own logged sessions, not a trained model.

**Why can the language model not be trusted with scheduling?** It can be wrong and cannot be tested exhaustively. The scheduler is a short algorithm (earliest deadline first with daily capacity) that I can test and explain. The model's time estimate can only widen the rule-based range, within half to double.

**How do you stop prompt injection?** The student's text is cleaned, wrapped as delimited data, and the model is told it is data. Its answer must match a strict JSON schema; sentences with numbers the facts do not support are thrown away; anything failing validation falls back to the rules. Hostile text is also tested ("ignore all previous instructions...") and ends up as an ordinary task title or is ignored.

**What does it cost, and what stops it running up a bill?** About 0.00045 US dollars per call at the default model's listed price (arithmetic, not a measurement), 40 calls per student per day at most, a monthly budget of 5 dollars after which all calls stop, and the student sets a spending limit in their own OpenAI account. Real usage is recorded in `ai_usage`.

**What data goes to the provider?** Only the text typed into the planner or assistant and the task numbers the question needs, and only for signed-in students with the AI switch on. Not names, e-mail, passwords, wellbeing answers or profile free text. Guests never reach the model.

**Does the plan change by itself?** Never. When energy, a deadline, a setting, a stress result or progress changes, the planner shows what would change and the student chooses.

**How does it learn from the student?** After each block: minutes, focus, how hard it felt, how the length felt, energy, finished or not, minutes left. Personal difficulty moves by 20% of the gap; the student's own "minutes left" overrides the estimate; finished tasks calibrate future estimates for that kind of work. Nothing is learned from data the student did not log.

**What is the accuracy of the estimates?** I do not know yet. The estimates come from rules and a small taxonomy and have not been validated against real students' times. I will report that as a limitation and, if the usability sessions give logged times, compare them. I have not claimed an accuracy figure anywhere.

**How do you know the wellbeing part is safe?** It says what it is: a screening aid that reproduces a survey dataset's scoring rule. It does not predict burnout, diagnose anything or understand emotions. A High result only offers a gentler plan. The Student Toolkit repeats this and points to student support.

**What does the Student Toolkit rest on?** Published studies on practice testing, spacing, interleaving, breaks, sleep, implementation intentions, estimation and procrastination, each with a "limits of the evidence" note. The notes are my short summaries; check the papers before quoting numbers.

**What are the weak points?** No live OpenAI or real-e-mail test yet; speed measured on a cloud machine with SQLite, not the laptop; no usability study yet; no screen-reader test. These are listed in `UPGRADE_20_ARCHITECTURE.md`, section 11.

**How is security evidenced?** 319 backend tests, 95 live probe checks across the OWASP Top 10 categories (including IDOR on the new endpoints, mass assignment on settings and profile, oversize inputs, forged guest state), and Argon2id, JWT expiry, rate limits and owner-scoped queries inherited from the earlier version.
