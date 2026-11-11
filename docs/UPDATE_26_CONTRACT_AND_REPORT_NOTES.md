# Update 26 - what the four-page version changes for the contract, the report and the viva

Read this before editing the report (due 13/11/2026 12:00). Facts only; nothing here is a claim that was not tested.

## 1. What was removed from the website (and what was not)
Removed from what a student can reach: Smart Planner (seven-page version), My Tasks, Student Toolkit, AI Learning Studio (packs, flashcards, sample pack), Settings (themes, reminders), My Profile page, How It Works page, Wellbeing check, Analytics, guest mode ("try without an account"), the energy check-in / ranked "what to do first" recommendation and Gentle (Burnout) Mode screens, in-app reminders.
Kept in the backend and its tests (about 500 tests still pass): the old routes and tables (tasks, roadmap, wellbeing, assist, studio). They are simply not used by the new website. Nothing was deleted from the database.
Removed from the frontend tests: the unit tests of the deleted pages (their backend tests remain). New frontend tests cover the four pages (40 frontend tests in total).

## 2. Conflicts with the signed contract (cannot be edited after submission)
- **Objective 3 (hybrid engine: deterministic scoring + LLM for justifications and offline-failure handling).** Now: the Study Planner is hybrid in the way the project description asks (AI writes, fixed rules check, built-in engine takes over when AI is off, offline or fails). BUT the "energy and deadline scoring that ranks tasks, with Burnout Mode" no longer has a screen. Mood and stress now only change how heavy the plan is. Say this plainly in the report. Ask the supervisor (Syed Muhammad Ali) to agree in writing; his signature line on the contract copy was blank.
- **Objective 2 (secure full-stack web app, CRUD, API, DB constraints).** Still met: authentication, CRUD for plans, tasks, notes and documents, validation, ownership checks, constraints, rate limits.
- **Objective 4 (unit, latency, security tests; usability evaluation).** Still met for the new endpoints (see UPDATE_26_TEST_RESULTS.md). The usability study is still not done.
- **The "offline burnout" idea in the project description** is now only the offline plan engine plus the lighter plan for tired / stressed students. The trained wellbeing model is not reachable from the website.

## 3. Report chapters that are now wrong and must be rewritten
Anything describing: seven pages; guest mode; Smart Planner scenarios; My Tasks confirmations and replanning; reminders; Student Toolkit; AI Learning Studio packs and flashcards; Settings and Profile pages; "no outside AI"; Wellbeing check as a feature; Burnout/Gentle Mode as a student-facing feature; screenshots of the old pages. The architecture, security, database and testing chapters stay mostly valid (add the new tables s_plans, s_tasks, s_notes, s_documents and the new endpoints). `docs/REPORT_REPLACEMENTS.md` and `docs/REPORT_UPDATE_25.md` describe the older version; they need a new matching file (not written here).

## 4. Honest status of the AI
No real AI service has been called by any test. AI plan writing and the quiz were tested with a scripted stand-in (the same code path, different provider object). Quiz questions and AI plan quality from a real model are unknown until you run `run-ai-smoke-test.bat` with your own key (see AI_ACTIVATION_GUIDE.md). The AI stays OFF by default. When it is switched on, plan text (subject, topic, notes, dates, mood, stress) and quiz document text go to the AI company; the page warns about this for quizzes.
