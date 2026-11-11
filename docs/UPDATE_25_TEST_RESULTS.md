# Update 25: what was really tested, with real results

Run on 29-30 October 2026 in the build environment (Linux, PostgreSQL 16, Python 3.13, Chromium). Every number below was printed by the tool named; none was typed in from memory. **Run the same tests on your own laptop and quote YOUR numbers in the report** (`run-tests.bat`, `run-e2e.bat`, `run-a11y-test.bat`, `run-security-test.bat`, `run-journey-test.bat`, `run-benchmark.bat`). Things that were not tested are listed at the end and in `KNOWN_LIMITATIONS.md`.

## Summary

| Layer | Tool | Result |
|---|---|---|
| Backend, in-memory SQLite | pytest | **446 passed** |
| Backend, real PostgreSQL 16 (all tables dropped and recreated per test) | pytest with `MINDSYNC_TEST_DATABASE_URL` | **446 passed** |
| Frontend | vitest (19 files) | **181 passed**; production build succeeds |
| Live security probe against the running API on PostgreSQL | `scripts/security_probe.py` | **159 / 159** checks passed (OWASP-mapped; the new checks cover roadmap, reminders, Studio, uploads, profile and e-mail change) |
| A student's week over HTTP on PostgreSQL | `scripts/journey_probe.py` | **48 / 48** (30 older + 18 new: roadmap saved, confirm, Dashboard moves, replan keeps history, reminders once, sample pack, quiz, no-AI message) |
| Seven-page browser test (real Chromium, real backend and database) | `e2e/browser_e2e_seven_pages.py` | **85 / 85** |
| Smart Planner browser scenarios 1-16 | `e2e/browser_e2e.py` | **65 / 65** with `E2E_TIMEZONE=Europe/Copenhagen` (see the note on time of day) |
| Accessibility (axe-core, WCAG 2.0/2.1 A and AA) | `e2e/a11y_audit.py` | **0 violations over 208 page states**: desktop and phone, light and dark, signed-in and guest, every Studio and My Tasks view, all five colour themes, larger text with readable contrast; keyboard and `lang` checks passed |
| Speed | `scripts/benchmark_latency.py api` | every endpoint measured **p95 under 3 s** (see below) |
| Smart Planner unchanged | pixel comparison of 16 screenshots, old build against new build | **identical** (see below) |

### Speed (50 requests each, one student, PostgreSQL on the same machine, AI never involved)
Highest single-user p95: `POST /assist/evaluate` 33 ms; `POST /roadmap/replan/preview` 30 ms; `GET /roadmap` 18 ms; `GET /reminders` 17 ms; `POST /studio/packs/{id}/quiz` 7 ms; `GET /studio/summary` 7 ms. Ten students at once, 100 requests: p95 316 ms, no failures. The 3-second target is for the whole round trip; these numbers do not include a real AI request, which was not made (the time of a real AI call depends on the provider and is **not measured**).

### Smart Planner unchanged (checked, not assumed)
The same four steps (empty form, filled form, roadmap, study session) were screenshotted in light and dark, desktop and phone with the build from before this work (`backup_before_update24`) and the new build, then compared pixel by pixel. The page content is **pixel-identical in all 8 desktop images**; in the 8 phone images it is identical apart from one 1-pixel difference in one image. The only other differences are the left menu / phone slide-out menu (seven items instead of five) and a bell in the phone top bar. To get this exact, two colour variables that were changed by the new colour themes were put back to their original values for the default blue theme.

## Your 31 required checks (Part 15), each with its real evidence

| # | Check | Evidence | Result |
|---|---|---|---|
| 1 | Smart Planner functional and visually unchanged | scenarios 1-16 of `browser_e2e.py` (65/65); pixel comparison above; existing planner tests in the 446 | pass |
| 2 | Roadmaps of different lengths save completely | `test_whole_roadmap_is_saved_for_short_and_long_plans` (3, 9, 30 and 70 days: every block, minute and day saved); browser check "the WHOLE roadmap is saved" | pass |
| 3 | Dates and weekdays correct | `test_every_day_has_the_right_weekday_and_label`, `test_the_students_study_days_are_respected...` (no weekend blocks when Monday-Friday chosen), `dayLabels.test.js` (month end, year end, clock change) | pass |
| 4 | Today and tomorrow show the right tasks | `test_today_and_tomorrow_lists`; browser (My Tasks Today / Tomorrow) | pass |
| 5 | Several subjects on one day | `test_several_subjects_can_share_one_day` | pass |
| 6-8 | Done / Partly done / Not done persist | `test_done_saves_status...`, `test_partly_done_keeps_the_rest...`, `test_not_done_and_delayed`; browser: saved, read back through the API after reload | pass |
| 9 | Delayed tasks can be rescheduled | `test_not_done_and_delayed`, `test_edit_move_add_remove_with_confirmation`; browser "Tomorrow marks a block Delayed" | pass |
| 10 | Overdue stays visible | `test_overdue_after_the_day_passes_and_stays_visible` | pass |
| 11 | Actual study time recorded accurately | `test_done_saves...` (minutes in = minutes out, summary and Dashboard); browser (20 + 10 = 30 min); journey probe (+20 min on the Dashboard) | pass |
| 12 | Accidental completion can be corrected | `test_changing_the_answer_replaces_it_instead_of_adding`, `test_undo_restores_everything`, `test_finishing_the_last_block...undo_reopens_it` | pass |
| 13 | New tasks and topics can be added | `test_edit_move_add_remove_with_confirmation`; browser (own block added) | pass (topics are added with a simpler form than Smart Planner, see limitation 7) |
| 14 | Replanning preserves history | `test_replan_preview_changes_nothing_and_apply_needs_confirmation`; journey probe; browser (done and minutes kept after a real replan) | pass |
| 15 | Manual edits not silently overwritten | `test_replan_warns_about_blocks_the_student_edited`; own blocks carried into the new plan | pass |
| 16 | Dashboard reflects real saved progress | `test_done_saves...` (dashboard numbers), journey probe, browser (Dashboard shows the confirmed progress and quiz result; says completion is not mastery) | pass |
| 17 | Daily reminders display correctly | `test_daily_and_deadline_reminders_are_created_once`, `test_reminder_rules_are_pure...`; browser (Reminders box, bell, "no email" note) | pass |
| 18 | Deadline reminders respect intervals | `test_reminder_rules_are_pure_and_honour_settings` (default 7, 3, 1, on the day, overdue; custom sets; switched off) | pass |
| 19 | Rescheduling updates reminders | `test_moving_work_updates_todays_reminder_and_changing_a_deadline_replaces_old_ones` | pass |
| 20 | Duplicate notifications prevented | unique key per student in the database; `test_daily_and_deadline_reminders_are_created_once`; journey probe (reload does not add reminders) | pass |
| 21 | Settings persist | `test_new_settings_validate`; browser (dark, purple, larger text, contrast, reminder time saved in the account and after reload) | pass |
| 22 | Profile editing works securely | `test_profile_account.py` (7 tests: validation, e-mail change, lock-out, deletion leaves no rows); browser (profile, password, e-mail, sign out, delete with wrong then right password); security probe | pass |
| 23 | Sample pack works without AI | `test_ai_off_by_default_sample_still_works`; browser (guest and signed in); journey probe | pass |
| 24 | Quiz scoring accurate | `test_quiz_is_marked_on_the_server_and_answers_are_not_sent_early`, `test_retry_incorrect_and_progress`, `test_bad_quiz_submissions_are_rejected`; guest twin tests (4 of 5 correct) | pass |
| 25 | Flashcard review history persists | `test_flashcards_spaced_repetition_and_due_list`; browser (box and review count read back from the database) | pass |
| 26 | Revision scheduling works | `test_srs_rules` (boxes and waiting days 0, 1, 3, 7, 14, 30; easy +2, okay +1, difficult back to box 1) and the guest copy of the same rules | pass |
| 27 | User data isolated | `test_other_students_cannot_touch_my_blocks`, `test_delete_pack_needs_confirmation_and_is_private`, security probe (student B cannot read, change, delete or answer student A's roadmap blocks, packs and reminders: all 404) | pass |
| 28 | Guest mode behaves appropriately | `guestRoadmap.test.js` (8), `guestStudio.test.js` (7); browser scenario I (plan, confirm, reload, sample pack, honest "AI not switched on", guest limits) | pass |
| 29 | Mobile layouts work | browser: no sideways scroll on all seven pages at 390 px, also with larger text, readable contrast and the pink theme; axe on phone; found and fixed a 6-pixel overflow in Settings with larger text | pass |
| 30 | Light and dark modes work | browser (all seven pages screenshotted in both and read); axe in both (208 states) | pass |
| 31 | Existing regression tests remain passing | the whole backend suite on both databases and the whole frontend suite (including all earlier tests) | pass |

## Problems found by this testing and fixed
* Account deletion did not remove the new tables' rows (roadmap history, reminders, learning packs). Fixed in `account.py`; PostgreSQL (which enforces foreign keys) now deletes cleanly and a test checks that no rows are left.
* An uploaded file name such as `../../etc/passwd.txt` was echoed back unchanged. It is now reduced to its last part (`passwd.txt`).
* The flashcard button's spoken name did not contain its visible text (axe rule `label-content-name-mismatch`). Fixed.
* Settings on a phone with larger text was 6 pixels too wide because of the time-zone list. Fixed and now tested on all pages.
* The new colour themes changed two colours of the default theme very slightly (up to 28 of 255); restored so the Smart Planner is pixel-identical. Dark-mode buttons also now follow the chosen colour theme.
* The website signed a student out if the server was merely busy when it checked the login; now only a real 401/403 does.
* The data export now includes the roadmap, reminders and learning packs. `docs/openapi.json` was out of date (34 routes) and was regenerated (89 routes).

## What was NOT tested
* **Any real AI service.** Gemini and OpenAI code was tested only against pretend servers; AI is off and no key exists.
* **Any real e-mail.** None is sent; this version has no e-mail delivery of reminders.
* Windows and your laptop's PostgreSQL; Firefox, Safari, a real phone; a screen reader; zoom to 400 %; real users; many simultaneous students.
* The migration of an existing database was tested on a copy created in this environment (new columns and tables were added, nothing deleted); take your own pgAdmin backup before first start.
* Time of day: browser scenarios that study "today's" first block fail in the late evening of the browser's time zone, because there is then correctly nothing left for today (see `KNOWN_LIMITATIONS.md`, item 13).
