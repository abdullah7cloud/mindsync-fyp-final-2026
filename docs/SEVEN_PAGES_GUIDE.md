> **Superseded by update 26.** The website now has four pages. See `FOUR_PAGES_GUIDE.md`. This guide describes the earlier seven-page version.

# MindSync: the seven pages, in plain English (update 25)

MindSync has exactly seven pages after you sign in (or continue as a guest). The idea that ties them together is one loop:

**Smart Planner makes the plan → the whole roadmap is saved → My Tasks shows it day by day → reminders nudge the student → the student confirms what really happened → the Dashboard updates → the next plan uses what was learned.**

Nothing in this loop needs AI. The only AI feature is the AI Learning Studio, and it is switched off until you choose to switch it on (see `AI_ACTIVATION_GUIDE.md`).

## 1. Smart Planner (unchanged)
The student fills in a short form (subjects, topics, deadlines, how much is done, how much time they have). MindSync's own rules estimate the work, check that it fits, and build a day-by-day roadmap that never plans more than the student's daily limit. This page was finished earlier and was **not redesigned** in this update. The only change is behind the scenes: the roadmap it makes is now saved in full, and the form can show the plan in My Tasks.

## 2. My Tasks (new): the daily roadmap and tracker
* Shows **"Day N of total"** and five views: **Today**, **Tomorrow**, **Full Roadmap**, **Completed**, **Overdue / Delayed**.
* The **whole roadmap** (every block of every day) is saved in the database, not only today's. Reloading, logging out and in again, or using another device shows the same roadmap.
* For each block the student presses **Done**, **Update progress** (partly done / not done / delay) or **Tomorrow**. A box asks "How did it go?", the real minutes studied and how it felt (easy / okay / difficult), and **Save My Progress** saves it. Answers can be changed or undone.
* The student can **edit** a block, **add** their own block or a whole topic, **move** (postpone) a block, or **remove** one after a confirmation question. Blocks the student changed are marked "Yours" and a new plan warns before replacing them.
* **Replan My Remaining Work** shows a preview (what is kept, what is replaced, what the new plan looks like) and changes nothing until the student presses "Yes, replace my remaining plan". Confirmed work and its minutes are always kept as history.
* Progress is **minutes the student confirmed, divided by minutes planned**. It is not a measure of how well the student knows the material, and the page says so.

## 3. Dashboard
Shows real progress only: roadmap progress ring and bars, planned versus studied hours by week, deadline cards (Upcoming, Due today, Overdue, Completed), confirmed progress by subject, daily and weekly numbers, streak and achievements, mood and stress trends from the optional check-in, and quiz results and revision reminders from the Learning Studio. A new student sees an honest empty state, not made-up numbers. "Completed" is never presented as "mastered".

## 4. Student Toolkit
Six groups of study techniques: **Focus and Concentration, Memory and Revision, Procrastination, Exam Preparation, Assignments and Projects, Study Wellbeing**. Each technique says what it is, why it works, how to do it (steps), gives an example, and states **the limits of the evidence**. Techniques backed by a study cite it (checked against the abstract); everyday habits not tied to a study we could check are labelled **"practical"** and say so. Nothing here is medical advice or a diagnosis, and there are no AI quizzes in the Toolkit (quizzes live in the Studio).

## 5. AI Learning Studio
* The student uploads notes (PDF, Word, PowerPoint, text, Markdown) or pastes text and presses **Create My Learning Pack**. The pack has lessons, multiple-choice questions (5, 10 or 15 per quiz; easy, medium, hard or mixed) with explanations, and flashcards.
* **The pack is made once and saved.** Quizzes ("Review Answers", "Retry Incorrect"), flashcards (Easy / Okay / Difficult with spaced repetition: harder cards come back sooner), progress and revision reminders all use the saved pack and **never call AI again**.
* **Today AI is off.** The page says "AI is not switched on yet" and the create form is switched off. The **"Try a Sample Learning Pack"** button opens a hand-written pack (3 lessons, 10 questions, 10 flashcards) so everything can be practised and demonstrated. It is labelled "Hand-written sample ... not made by AI" everywhere. Guests can practise the sample too; making a pack from your own notes needs an account and AI switched on.

## 6. Settings
Light, dark or "same as my device"; five colour themes (Blue, Purple, Green, Pink, Neutral) that all keep text readable; normal or larger text; readable (high) contrast; reduce motion; study time limits and preferences; reminder settings (turn in-app reminders on/off, daily reminder time, which deadline warnings: default **7, 3 and 1 days before, plus on the day, plus overdue**); AI help on/off; privacy: download my data, erase my check-in results. Every visible setting works and is saved in the account (guests: in the browser). There are no keys, mail-server, database or debug settings on this page. The email-reminder option is shown as not available yet.

## 7. My Profile
Picture (one of eight ready-made pictures; photos are not uploaded, which avoids storing unsafe files), full name, display name, e-mail, optional phone number, level and field of study, year, study goals, weekly goal, academic summary, subjects and strengths. Under **Sign-in and security**: **change password** (asks for the current one), **change e-mail** (asks for the password; no confirmation mail in this version), **sign out**, and **delete account** (asks for the password; erases everything including the roadmap and learning packs). A guest sees what a guest cannot do and a link to create a free account.

## Reminders (in-app only)
* **Daily study reminder** from the time chosen in Settings (default 08:00): a greeting, today's blocks with a link to My Tasks, a preview of tomorrow, and how many blocks are overdue. It is created once per day (never twice), and updates if the roadmap changes.
* **Deadline reminders** at the chosen distances before each deadline, on the day, and when overdue. Unfinished work stays visible as Overdue and is never silently dropped. When a deadline changes the old reminder is replaced.
* They appear in the bell at the top and in the Reminders box on My Tasks. **No email or text message is sent.** The student's timezone decides what "today" means.

## 90-second answers for questions you may be asked

* **"Where does AI come in?"** Only in the Learning Studio, once per new set of notes, to write the pack. The study plan, the scheduling, the minutes, the quiz marking and the flashcard schedule are MindSync's own deterministic rules. AI is off today, so the whole project works offline.
* **"How do you stop AI cost and abuse?"** Server-side limits for text size, uploads, attempts per student and per day, a time limit, a duplicate guard (the same notes never cost twice), a budget, and the key lives only on the server. See the table in `AI_ACTIVATION_GUIDE.md`.
* **"What if the AI writes rubbish or something harmful?"** Output is validated before saving (plain text only, valid answers, must match the student's own notes, minimum sizes) and dropped otherwise. Notes are treated as data, not instructions.
* **"Is completing tasks the same as learning?"** No, and the pages say so. The Dashboard reports confirmed study time and quiz scores as practice, not mastery.
* **"Is the data safe?"** Passwords use Argon2id; every route checks the logged-in student (tested with a second student trying to read, change or delete the first student's roadmap, packs and reminders); inputs are validated; uploads are checked by type, size and content; `docs/security_test_results.md` lists the checks that were run and their real results.
* **"What does not work yet?"** See `KNOWN_LIMITATIONS.md`.

## Demo script (about 10 minutes)

1. **(1 min) The loop.** Say the one-line loop above. Show the menu: seven pages.
2. **(2 min) Smart Planner → My Tasks.** Make a plan from two subjects (or use the prepared account). Open My Tasks: "Day 1 of N", Full Roadmap shows every day. Say: "the whole roadmap is saved in PostgreSQL". Reload the page to prove it.
3. **(2 min) Confirm progress.** Press Done on today's first block, enter 20 minutes, "Okay", Save My Progress. Open the Dashboard: the ring and "studied" numbers moved. Say: "it counts only what I confirmed, and it is not the same as mastery".
4. **(1 min) Honest replanning.** Press Tomorrow on another block, then Replan My Remaining Work: show the preview and press Cancel. Say: "nothing changes until I confirm, and my confirmed work stays".
5. **(1 min) Reminders.** Show the bell/Reminders box and the note "No email or text message is sent in this version".
6. **(2 min) Learning Studio.** Say the five-step sentence: "notes in, AI writes the pack once, it is saved, quizzes and flashcards use the saved pack, AI is only used again for new notes". Show "AI is not switched on yet", press "Try a Sample Learning Pack", take a 5-question quiz, open Review Answers and Retry Incorrect, rate one flashcard.
7. **(1 min) Settings and Profile.** Switch dark mode and the purple theme (they stay after reload); show the profile picture and the Sign-in and security box.

Have a backup: the guest mode needs no account and shows the same pages, so the demo still works if the server is down.
