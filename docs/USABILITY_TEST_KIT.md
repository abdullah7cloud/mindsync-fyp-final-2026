# MindSync Usability Test Kit (Objective 4: "evaluate usability and efficiency")

Aim: 5-8 students try MindSync for ~15 minutes each and fill in a short questionnaire. You then report the numbers in Chapter 4/5. Use REAL people and REAL answers only - never invent results.

## 1. Before you start (10 minutes)
1. Start the backend and frontend (`start-backend.bat`, `start-frontend.bat`).
2. Open http://localhost:5173 on your laptop. Let the participant use your laptop (or run it on theirs).
3. Have them use a NEW account (register inside the test) so your own data is not shown.
4. Ask them to read the consent text below out loud / on screen.

## 2. Consent text (read to each participant)
"I am testing my final-year project, MindSync. It takes about 15 minutes. I am testing the software, not you. You can stop at any time. I will record only your answers and your task times - no names. The results will be used anonymously in my university report. Do you agree to take part?"  (Write "P1", "P2"... in the sheet, not names.)

## 3. Tasks (give one at a time, time each with your phone)
| # | Task to read out | What success looks like |
|---|---|---|
| 1 | "Create an account and log in." | Reaches the dashboard |
| 2 | "Add a task called 'Maths homework', difficulty 4, due tomorrow." | Task appears in the list |
| 3 | "Tell the app you are feeling very tired." (energy 1 or 2) | Burnout Mode shows On |
| 4 | "Which task does MindSync recommend now, and why?" | They find the recommendation + explanation |
| 5 | "Mark the task as done, then start a focus timer." | Task completed, timer running |
Record: completed (yes/no), seconds taken, anything they said or got stuck on.

## 4. SUS questionnaire (give on paper or a phone form; 1 = strongly disagree ... 5 = strongly agree)
1. I think that I would like to use MindSync frequently.
2. I found MindSync unnecessarily complex.
3. I thought MindSync was easy to use.
4. I think that I would need the support of a technical person to be able to use MindSync.
5. I found the various functions in MindSync were well integrated.
6. I thought there was too much inconsistency in MindSync.
7. I would imagine that most people would learn to use MindSync very quickly.
8. I found MindSync very cumbersome to use.
9. I felt very confident using MindSync.
10. I needed to learn a lot of things before I could get going with MindSync.

Extra open questions: (a) What did you like most? (b) What was confusing? (c) Did the explanation of why a task was recommended help you? (d) Did Burnout Mode feel helpful or annoying?

## 5. Record and score
1. Copy `docs/usability_results_template.csv` to `docs/usability_results.csv` and type each participant's answers (q1-q10) and task data.
2. In `backend` run: `python -m scripts.sus_score` (or add a double-click helper later). It writes `docs/usability_summary.md` with the mean SUS score.
3. SUS benchmark: about 68 is average, 80+ is excellent. Report mean, range, number of participants, and task completion rate.

## 6. What to write in the report
- Method: number of participants, how recruited (e.g. fellow students), tasks, SUS.
- Results table (from usability_summary.md) + 2-3 quotes from comments.
- Limitations: small sample, students you know, short session (say this honestly - it is worth marks in Critical Analysis).
- Changes you made because of feedback (even one small change counts).
