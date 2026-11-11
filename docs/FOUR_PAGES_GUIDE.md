# MindSync - the four-page version (update 26)

A student logs in and sees four pages and nothing else: **Dashboard, Study Planner, AI Learning Zone, My Notebook**. Account settings are a small window ("My account"). The design (colours, photos, theme) is unchanged.

## What each page does

**Dashboard.** Total, completed and remaining tasks. One progress bar (finished tasks / all tasks, shown as a percent). Upcoming deadlines (one line per study plan). Overdue tasks. The task list with a tick box for each task. Ticking a task saves at once and the numbers and the bar change. A "Create Study Plan" button goes to the Study Planner.

**Study Planner.** One form: Subject Name; Topic Name; Learning Goal / Notes; Target Completion Date; Current Mood (Good / Okay / Tired); Stress Level (Low / Medium / High); one button "Generate My Study Plan". The result is a short learning roadmap and single tasks with a day, a start time and minutes. Every task is on or before the target date. The student can tick, edit or delete a task, edit the plan (including the roadmap), or delete the whole plan. The page says honestly who made the plan: "Made by AI and checked by MindSync", or "Made offline" by the built-in rules.

**AI Learning Zone.** One thing only: an AI quiz. Upload a PDF, Word or text file (or press "Create Quiz" on a document in My Notebook), press "Generate Quiz", answer the multiple-choice questions, see the final score, the correct answers with short explanations, and try again. The quiz is saved, so trying again does not use the AI a second time. No chatbot. If the AI is off or offline the page says so; it never shows a fake quiz.

**My Notebook.** One page, two sections.
- *My Notes*: new note with a title and a comfortable writing area, save to the account, edit, delete (asks first), search by words in the title or text, download as PDF or Word. It warns about unsaved changes.
- *My Documents*: upload PDF, Word, PowerPoint or text files; view (a PDF opens in the page; Word and PowerPoint show their text); download; rename; delete (asks first); "Create Quiz" opens the AI Learning Zone with that document.
A "My Notebook" shortcut sits in the top bar of every page so notes are one click away while studying.

**Account** (the "My account" button in the menu or your name at the top): change name, change password, download my data, delete my account (asks for the password), log out. Register, Login, Forgot password and Reset password stay as before.

## How a plan is made (the hybrid)
1. Online and AI switched on: the AI writes the whole plan (roadmap, tasks, dates, times).
2. MindSync checks the AI plan with fixed rules (task count, dates inside today..target, 10-180 minutes per task, sensible times, a daily limit that is gentler when mood is Tired or stress is High, plain text only). A plan that fails is thrown away.
3. AI off, offline, too slow, over its daily or monthly limit, or failed check: the built-in engine makes the plan on the server with no outside service. The page tells the student which happened.
4. The quiz always needs the AI. Without it the page says it is not available.

## A 5-minute demo for the viva
Register -> Dashboard is empty (0 / 0 / 0) -> "Create Study Plan" -> fill the form (pick Tired + High) -> Generate -> show roadmap, tasks, "Made offline" or "Made by AI" -> Dashboard: numbers, deadline, tick two tasks, bar moves -> My Notebook: write a note, search, download PDF -> My Documents: upload a PDF, View, rename -> "Create Quiz" -> (if AI is on) Generate Quiz, answer, score -> log out, log in, everything is still there.

## Limits worth knowing
Notes: 500 per student, 60,000 characters each. Documents: 40 per student, 10 MB each. Plans: 30, with up to 40 tasks each. PDF downloads of notes handle Latin letters (other alphabets become "?"; the Word download keeps every letter). A student can make 8 plans per 10 minutes.
