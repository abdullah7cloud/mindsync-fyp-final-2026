# Explaining MindSync to your professor, in simple English

Use these short answers. Each one has a practical example you can show on screen. Nothing here claims that AI or email is switched on, because neither is.

## 1. What do the seven pages do?
See `SEVEN_PAGES_GUIDE.md`. In one line each: **Smart Planner** makes the plan. **My Tasks** is where you do it day by day and say what really happened. **Dashboard** shows your real progress. **Student Toolkit** teaches study techniques and says how strong the evidence is. **AI Learning Studio** turns notes into a quiz and flashcards. **Settings** changes how the app looks and when it reminds you. **My Profile** is you and your account.

## 2. How does Smart Planner create a roadmap?
You tell it your subjects, topics, deadlines, how much is already done and how many minutes you can study each day. For each topic it **estimates the work** (for example "an exam with 4 chapters you understand a little: about 8 hours, between 6 and 11") using fixed rules plus what it has learned from your own past sessions. Then it **checks the plan fits** before the deadline and builds it **day by day**, never putting more on a day than your daily limit, giving the closest deadline first, spreading the rest, and keeping a spare day if you ask for one. If it does not fit, it says so honestly instead of pretending.
*Example:* a stats exam in 9 days and a report in 12 days, 2 hours a day → about 11 study days, each with one or two blocks of 35-60 minutes.

## 3. How is the roadmap saved in PostgreSQL?
Every block of every day becomes **one row** in the table `plan_sessions` (day, minutes, topic, status, the minutes you really studied, how it felt). The plan itself is a row in `study_plans`. A history of changes is kept in `plan_events`. So the **whole** roadmap is saved, not only today. When you log in on another device the same rows are read back.

## 4. How does My Tasks manage daily study work?
It reads those rows. **Today** and **Tomorrow** show the blocks for those dates, **Full Roadmap** shows every day, **Completed** shows what you confirmed, **Overdue / Delayed** shows what was missed or moved. For each block you press Done, Update progress or Tomorrow. Everything you press is saved straight away, and nothing is lost: a missed block stays visible as Overdue until you deal with it.

## 5. How does completing a task update the Dashboard?
When you press **Save My Progress** the block's row is updated (status "done", minutes studied, how it felt). The Dashboard does not keep its own copy: it **adds up the same rows**. So after you confirm 20 minutes, "Time studied" goes up by 20 and the progress ring moves. The ring is *confirmed minutes ÷ planned minutes*. It says "completing blocks is not the same as mastering the material", because it measures effort, not understanding.

## 6. How do reminders and deadlines work?
Every time you open the app the server checks the rules: *has the daily reminder time passed today, and is there not yet a reminder for today?* If so it creates one reminder (a unique key such as `daily:2026-11-02` makes a second one impossible). For deadlines it uses the distances you chose in Settings (default 7, 3 and 1 days before, on the day, and overdue) and keeps only the nearest one that applies. If you move work or change a deadline, the old reminder is replaced. Reminders appear **inside MindSync** only (bell and My Tasks). **No email or text message is sent.**

## 7. How does quiz scoring work without AI?
Each saved question has four options and one stored right answer, and an explanation. When you answer, the **server compares your choice with the stored answer** (the quiz sent to your browser does not contain the answers, so they cannot be read early). Score = right answers ÷ questions. "Review Answers" shows each question, your answer, the right answer and the explanation; "Retry Incorrect" asks only the ones you got wrong. No AI is needed because the answers were stored when the pack was made.

## 8. How does spaced revision work?
Each flashcard sits in a **box from 0 (new) to 5 (well known)**. After you rate a card: *Easy* moves it up two boxes, *Okay* one box, *Difficult* puts it back in box 1. Each box has a waiting time: box 1 = 1 day, box 2 = 3 days, box 3 = 7 days, box 4 = 14 days, box 5 = 30 days. A card is "due" when its date arrives. So cards you find hard come back soon and cards you know come back rarely. It is plain arithmetic on dates (a Leitner system), not AI. The Dashboard shows "flashcards due today" as a revision reminder.

## 9. What does the deterministic scheduling engine do?
"Deterministic" means **the same input always gives the same plan**. It uses fixed, readable rules for estimating time, checking feasibility and placing blocks. That is why the plan can be explained, tested and trusted. AI is never allowed to change minutes, order or deadlines; it may only help word text, and today it is off.

## 10. What will AI do when activated later?
Only two things: (a) in the **Learning Studio**, turn pasted notes into a learning pack **once** and MindSync saves it; (b) optionally help understand typed text and explain a plan in words. It is switched on by you with a key in `backend\.env` (see `AI_ACTIVATION_GUIDE.md`). Server-side limits stop abuse and cost. If the AI is slow, wrong or offline, MindSync keeps working with its own rules.

## 11. How does authentication protect student information?
* Passwords are stored only as an **Argon2id** hash (never the password itself).
* After login you get a signed **JWT token** that expires; the server checks it on every request and uses the user ID **inside the token**, never an ID from the browser, so one student cannot ask for another's data. This was tested: a second student tried to read, change and delete the first student's roadmap blocks, learning packs and reminders and always got "not found".
* Too many wrong passwords lock the login for a while (brute-force protection).
* All input is checked by strict schemas (wrong types, huge numbers, extra fields and markup are rejected); database queries are parameterised (SQL injection tested).
* Uploaded files are checked for type, size and content and are read as plain text only, never run or stored.
* Deleting an account erases everything about the student, including the roadmap and learning packs; the data export lets the student see what is stored.
* The 159 live security checks are in `security_test_results.md` (mapped to the OWASP Top 10).

## Two-sentence summary to open with
"MindSync turns deadlines into a realistic day-by-day roadmap using fixed, explainable rules, saves the whole roadmap, and lets the student confirm what really happened so the Dashboard shows true progress. An optional AI feature turns study notes into a quiz and flashcards once, saves them, and everything after that works without AI."
