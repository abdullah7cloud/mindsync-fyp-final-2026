# Viva questions for update 21 (answers you can defend)

**Q1. What is intelligent about it if the scheduling is rules?**
The intelligence is in choosing the right amount and kind of work. The same words "exam" and "report" produce different step sequences, session lengths, workload ranges and difficulty. The estimate is corrected from the student's own sessions. Whole-plan feasibility (several tasks sharing one calendar) is something a per-task planner cannot see: in a measured test, the previous version planned three tasks separately and reported each as if it had all the time; the new one said the three together were short by about 21 hours.

**Q2. Why not just ask an LLM to plan?**
It would be slower, costlier, and could invent times that do not fit the calendar. The hard guarantees (no day over its limit, deadlines respected or the shortfall stated) come from code that is tested on random task sets. The LLM, when switched on, only reads free text and writes wording, and its numbers must match the facts or the answer is discarded.

**Q3. Is any of this trained by you?**
Yes: the wellbeing model (logistic regression on a public survey dataset; it recovers that dataset's scoring rule, it is not a diagnosis) and a task-fit model on simulated data (off by default). The planner, estimator and scheduler are rules plus per-student calibration. The OpenAI model is external and optional.

**Q4. How do you prevent prompt injection?**
Student text is sent as delimited data; the model must answer in a strict JSON schema; the reply is validated (schema, numbers supported by facts, no links, markup, key-like strings or instructions the student did not type); the model cannot call tools or touch the database; the key never leaves the backend. Tested with a local stand-in that returns hostile answers (18/18). It reduces the risk; it cannot be proven absent.

**Q5. What does it cost and what stops runaway cost?**
Checked on 29 Oct 2026: 0.10 / 0.50 US dollars per million input / output tokens for the chosen model. An assumed typical call (the figure used in the test) is about 1 500 tokens in and 600 out, i.e. fractions of a cent. Controls: off without a key, student switch, guests excluded, 40 calls a day per student, 5 US dollars a month, plus your own limit set in your OpenAI account. Prices change; re-check before use.

**Q6. How accurate are the time estimates?**
Not validated against real students. They are ranges built from counts (words, pages, slides, chapters), listed items, or the size of the task, times typical minutes per unit, scaled by skill and history. State this as a limitation and propose the study that would validate them (estimated against logged minutes).

**Q7. What did testing find?**
Real defects (listed in `UPGRADE_21_SUMMARY.md`), e.g. a large maths exam estimated smaller than a short quiz, a guest dashboard server error, links accepted in a model-written title, and 10 accessibility violations in the calendar and chart. Each got a regression test. Say that the first runs failed; that is the point of testing.

**Q8. What about accessibility?**
Automated axe-core audit, WCAG 2.0/2.1 A and AA, 16 page states at desktop and phone width: 0 violations after fixes; keyboard reach and visible focus checked; reduced-motion respected. Not done: screen reader walk-through, 400 % zoom, tests with assistive-technology users. Automated tools find only part of the problems.

**Q9. What about privacy and data?**
Guests: data stays in the browser. Accounts: everything is scoped to the user; export, erase and delete are available; nothing about the account (e-mail, name) is sent to the AI provider; the usage table stores counts and cost, not the student's text.

**Q10. What would you do with more time?**
Usability study with SUS, compare estimates to logged minutes, collect real wellbeing outcomes with consent, add a calendar import, evaluate other models, and test live delivery of e-mail reminders with several providers.
