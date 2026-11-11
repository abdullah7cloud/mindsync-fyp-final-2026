# MindSync - final verification (29 October 2026)

All of this was run in the build environment (Linux; PostgreSQL 16 and SQLite). **Nothing was run on the student's laptop, on Windows, on PostgreSQL 18, with a real OpenAI key or with a real mail provider.**

## Verified
| What | Result |
|---|---|
| Backend tests, SQLite | 338 passed |
| Backend tests, PostgreSQL 16 | 338 passed (`MINDSYNC_TEST_DATABASE_URL`, see below) |
| Frontend tests / production build | 140 passed / build succeeds |
| Journey probe against the PostgreSQL-backed API | 30 / 30 (`journey_results.md`) |
| Live security probe (OWASP Top 10 categories) | 95 / 95 |
| Browser end-to-end (real Chromium) | 162 / 162 |
| Accessibility (axe-core, 16 page states, automated only) | 0 violations |
| Optional OpenAI layer vs local stand-in server | 18 / 18 |
| E-mail reminders vs local SMTP sink | 22 / 22 |
| `database/schema.sql` | defect found and fixed: 3 of 18 tables were missing; a test now guards it |
| Upgrade path from the previous version | new tables are created at start-up by `ensure_schema()` |
| Windows `.bat` files | static review and corrections only (CRLF, UTF-8, Playwright/Chrome); **not executed on Windows** |

## Not verified (cannot be done by the build)
Live OpenAI call; real SMTP delivery; laptop run (Windows, Python 3.14, PostgreSQL 18); `.bat` files executed on Windows; usability study; screen-reader test; estimate accuracy on real students.

## Running the backend tests on PostgreSQL
Create an empty database and user, then (the test fixture drops and re-creates all tables in that database - use a throw-away one):

    set MINDSYNC_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/mindsync_test
    cd backend
    python -m pytest -q

Without the variable the tests use in-memory SQLite.

## Regenerating the ERD from the code
`python backend/scripts/make_erd.py`, then `mmdc -i docs/diagrams/erd_current.mmd -o docs/diagrams/erd_current.png -s 2 -b white`.
Every student-owned table has a `user_id` foreign key to `users`; those lines are left out of the picture so it stays readable.

## Student actions
See `SUBMISSION_CHECKLIST.md`.

## Found and fixed during the final check
- The dashboard's weekly numbers read a stored time wrongly when the test machine's own clock was behind UTC (SQLite only; PostgreSQL was not affected). Fixed in `app/assist/summary.py`, regression test added (338 backend tests now). The suite passes with the machine time zone set to Los Angeles, UTC, Copenhagen and Auckland.
- `greenlet` is now listed in `requirements.txt`; on a fresh Windows install with the newest SQLAlchemy it was not installed automatically and the backend failed to start (seen on the student's laptop, fixed by installing it).
- One first run on PostgreSQL after a cold server start showed 1 failure that I could not reproduce; the next two full runs passed 338/338.
