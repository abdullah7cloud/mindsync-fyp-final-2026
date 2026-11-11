# MindSync - submission checklist (updated 29 Oct 2026, update 21)

## Dates
- Final report (Turnitin), code and 10 signed meeting notes (GitHub): **13/11/2026 12:00** | Viva: by **04/12/2026 17:00**

## Built and tested in the build environment (evidence in `docs/`)
- [x] React + FastAPI + PostgreSQL schema, JWT, Argon2id, validation (Pydantic + database CHECK constraints)
- [x] Smart Planner: free text -> drafts -> whole-plan evaluation -> accept -> timer -> feedback -> replan offer (`UPGRADE_20_ARCHITECTURE.md`)
- [x] Task-aware estimates and measured fixes (`UPGRADE_21_INTELLIGENCE.md`, `intelligence_results.md`)
- [x] Optional OpenAI layer with guards, validation, caps and fallback (`AI_MODEL_SELECTION.md`, `ai_integration_results.md` 18/18, diagram `diagrams/ai_guard_flow.png`)
- [x] E-mail reminders (lead times, same-day, overdue, duplicates, retry, time zones) against a local SMTP sink (`email_integration_results.md` 22/22)
- [x] Backend 338 tests (also 338 on PostgreSQL 16), frontend 140 tests, browser 162/162, journey probe 30/30, security probe 95/95, accessibility 0 axe violations (16 states)
- [x] Architecture, ERD, wireframes, AI flow diagrams (`docs/diagrams/`)
- [x] Demo script (`DEMO_SCENARIO.md`), viva answers (`VIVA_PREP.md`, `VIVA_QA_UPGRADE_20.md`, `VIVA_QA_UPGRADE_21.md`), report accuracy notes (`REPORT_ACCURACY_NOTES.md`)

## You must do yourself (nothing here was or could be done by the build)
- [ ] Install update 21 on the laptop (`UPDATE_21_START_HERE.txt`) and run every `.bat` test there; keep the logs in `_update_backup\logs`. **Quote only your own laptop numbers in the report.**
- [ ] Re-run `run-benchmark.bat` on the laptop with PostgreSQL just before the viva (target: under 3 s end to end).
- [ ] OPTIONAL: create an OpenAI key in your own account, set a monthly limit there, put it in `backend\.env`, make one real call and check the daily count in Settings. Without this the report must say the live call was **not** tested.
- [ ] OPTIONAL: send one real reminder with a Gmail App password (`docs/EMAIL_ALERTS.md`); otherwise say live delivery was not tested.
- [ ] Update the report: replace the sentences listed in `REPORT_ACCURACY_NOTES.md` (replace, do not add words).
- [ ] Usability test with real participants (`USABILITY_TEST_KIT.md`, `scripts/sus_score.py`).
- [ ] Ask the dataset authors or supervisor whether the wellbeing dataset is real or generated and write the answer in the report.
- [ ] 10 signed supervisor meeting notes (`MEETING_NOTES_TEMPLATE.md`); confirm in writing with the supervisor that the LLM/ML approach satisfies the "train an AI model" expectation.
- [ ] GitHub push (`GITHUB_PUSH_GUIDE.md`). **Never commit `backend\.env`.** Check `git status` before pushing.
- [ ] Turnitin upload; rehearse `DEMO_SCENARIO.md` twice.

## Known limitations (state them, do not hide them)
- Estimates are design assumptions shown as ranges; not validated on real students.
- The wellbeing model reproduces its dataset's scoring rule; it is not a diagnosis and does not predict burnout.
- No screen-reader or assistive-technology user test; automated audit only.
- Free-text understanding without the language model uses a word list; unusual wording makes the app ask a question.
- Live OpenAI and live SMTP behaviour untested here; the stand-in tests cover MindSync's side only.

## Final verification (29 Oct 2026)
- Full verified / not-verified lists: `FINAL_VERIFICATION.md`. Exact report wording: `REPORT_REPLACEMENTS.md` (net -91 words).
- Replace Figure 4.2 (ERD) with `docs/diagrams/erd_current.png` (18 tables) and update Figure 4.1 to show the optional language model.
