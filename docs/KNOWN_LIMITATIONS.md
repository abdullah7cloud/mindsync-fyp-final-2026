# Known limitations (update 26 - four-page version; items 1-14 are from update 25, items about the old seven pages no longer apply to what the student sees) — read before you write the report or give the demo

These are real. Do not describe the project as better than this.

1. **AI is not switched on and has never been tested against a real AI service.** The Gemini and OpenAI code was tested only with pretend servers. Pack quality from a real model is unknown. The first real test is yours (`run-ai-smoke-test.bat`).
2. **Email delivery is not available.** Reminders are in-app only. Changing the sign-in e-mail is protected by the password but sends no confirmation e-mail.
3. **Profile pictures are eight presets**, not uploads (a deliberate safety choice).
4. **Free-tier privacy:** if you later use the free Gemini plan, Google may use what students upload to improve its products. Students are warned and must tick consent; do not use private material.
5. **Scanned PDFs and pictures cannot be read** (no text recognition). Encrypted PDFs are refused. Documents longer than about 6,000 words must be split.
6. **A guest's data lives only in one browser.** Clearing the browser loses it. Guests cannot make packs from their own notes. The "history of changes" list in My Tasks is empty for guests.
7. **"Add a topic" in My Tasks is simpler than the Smart Planner form** (name, subject, deadline, minutes). Detailed follow-up questions (for example number of chapters) are only in Smart Planner.
8. **Quiz and flashcard quality for the sample pack** is hand-written and small (10 questions, 10 flashcards, 3 lessons). It demonstrates the mechanics, not a full course.
9. **Progress is time-based.** It measures confirmed study time and quiz results, not understanding. The estimates can be wrong; the app asks for the real minutes so it can improve.
10. **No payments or subscriptions exist.** A premium tier is only a prepared hook in the limits code.
11. **Not tested:** a screen reader (NVDA/VoiceOver), zoom to 400 %, real users, a real mail server, more than a few simultaneous students, Safari and Firefox (tests ran in Chromium). Automated accessibility checks (axe) cover about a third of real accessibility problems.
12. **Wellbeing screening is not a diagnosis** and was trained on survey-derived labels (see `WELLBEING_MODEL.md`).
13. **Browser tests depend on the time of day in the browser's time zone.** Late in the local evening a plan correctly has nothing left for "today" (My Tasks then says "A rest day is part of a good plan"), but several scripted scenarios start by studying today's first block. They failed when the test machine's browser time zone was in the evening (Los Angeles, about 20:00) and passed when the browser time zone was set with `E2E_TIMEZONE=Europe/Copenhagen` (65 of 65). The seven-page test now uses the whole roadmap for guests so it does not depend on this. In addition, during testing three older checks failed once in one full run (after logging out and in again the plan form was not shown; a profile check; a dashboard check) and passed on rerun; I could not reproduce that in 14 attempts, so **that cause is not proven**. As a precaution the website no longer signs a student out when the server is only briefly busy (only a real 401/403 does). Treat the second point as an open observation.
14. **No usability study or supervisor approval is claimed.** `USABILITY_TEST_KIT.md` is a kit to run one; no results exist.

## Added in update 26
15. **Only four pages are reachable.** Features of the seven-page version (Smart Planner scenarios, My Tasks confirmations, reminders, Toolkit, Studio packs and flashcards, Settings themes, Profile page, wellbeing check, guest mode) were removed from the website. Their backend code and tests still exist but nothing in the website uses them. See `UPDATE_26_CONTRACT_AND_REPORT_NOTES.md` (contract conflict, report chapters to rewrite).
16. **No real AI has been tried for plans or quizzes.** Only a scripted stand-in. Real question quality, answer correctness and plan quality are unknown. AI is OFF by default.
17. **Quiz needs the AI.** Offline or AI off: no quiz (honest message), by design.
18. **Note PDF export is Latin letters only** (other alphabets show as "?"). The Word export keeps all letters.
19. **Scanned PDFs / pictures cannot become a quiz** (no text recognition). A document must have 300 to 24,000 readable characters for a quiz.
20. **The AI sees plan details when AI is on:** subject, topic, notes, dates, mood and stress go to the AI company. Do not type private information in the notes box.
21. **No real e-mail is sent** unless a mail server is set up (see `EMAIL_ALERTS.md`). **No undo** after deleting a note, document, task or plan (each asks first).
22. **The "today" in a plan uses the browser's time zone.** Late in the evening a plan for today may correctly have no time left; the built-in engine then makes one short "Quick review" task.
23. **One legacy backend test depends on the time of day** and is skipped late in the evening (it also did in update 25).
