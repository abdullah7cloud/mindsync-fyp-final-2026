# Update 26 - what was really tested (four-page version)

Date of the runs: 30 Oct 2026, in the cloud workspace (Linux, PostgreSQL 16, Chromium). Your own laptop run is still needed for the numbers you quote (speed, Windows).

| Test | Result |
|---|---|
| Backend automated tests (pytest), SQLite | 502 passed, 1 skipped |
| Backend automated tests, PostgreSQL 16 | 502 passed, 1 skipped |
| New backend tests: study planner / dashboard (`tests/test_simple.py`) | 40 tests, included above |
| New backend tests: notebook (`tests/test_notebook.py`) | 17 tests, included above |
| Frontend tests (vitest) | 40 passed |
| Browser journey, AI stand-in ON (`e2e/browser_e2e_four_pages.py`) | 62 / 62 checks |
| Browser journey, AI OFF (`--ai-off`) | 58 / 58 checks |
| Live security probe of the new endpoints (`backend/scripts/security_probe_four_pages.py`) | 59 / 59 checks |
| Accessibility, axe-core WCAG 2.0/2.1 A + AA (`e2e/a11y_audit_four_pages.py`) | 0 violations on 15 screens/states x desktop and phone; keyboard-only plan creation works |
| Phone layout (390 px wide) | no sideways scroll on all four pages |

The browser journey covers: register, menu has exactly four pages, plan form and its six fields, plan made (AI and offline), dashboard numbers and bar, ticking and un-ticking, edit / delete task, edit / delete plan, notes (create, edit, search, PDF, Word, delete), documents (upload PDF / Word / text, refuse a fake file, view, download, rename, delete), quiz from a Notebook document and from a direct upload (score, correct answers, retry), everything still there after log out / log in, account window (name, password, data export, delete account), phone layout.

Bugs found by these tests and fixed during the update: note and document downloads failed in the browser (wrong return value); tall empty task rows and a 4-column tile row (CSS); the AI-off message mentioned a sample pack that no longer exists; the top-bar account button name did not contain its visible text (axe, phone); a note could be edited while it was still loading.

## NOT tested
A real AI service (plan writing or quiz quality); a screen reader; Safari / Firefox / Edge; Windows; many students at once; real e-mail; a usability study with real students; the speed numbers on your laptop (run `run-benchmark.bat`). In the browser tests a web-font request was blocked by the cloud workspace; fonts were not checked.
