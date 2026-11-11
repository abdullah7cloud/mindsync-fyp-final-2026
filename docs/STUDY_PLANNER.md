# Study Planner

Added 7 Oct 2026; made fully local 21 Oct 2026 (extension beyond the signed contract, following the professor's "add what you want" feedback).

## What the student does
1. Picks a **category** (e.g. Computer Science) and types the **topics** they want to learn, one per line.
2. Optionally chooses their **energy** (default: automatic from the latest check-in) and **how much time** they have.
3. Presses *Rate topics & build my plan*. Each topic gets a difficulty (1-5) and a time estimate. Any slider can be dragged; the plan rebuilds instantly.
4. Follows the timed plan, ticking each focus block. *Add these topics to my task list* turns the topics into normal tasks (ranked by the main recommender, covered by email alerts when logged in).

## How difficulty is rated (rules, no AI)
* A **known-topic table** (e.g. HTML = 1, SQL = 3, machine learning = 4) plus **keywords** (`basics`, `intro` = easier; `advanced`, `algorithm`, `proof` = harder); long topics +1. The matched phrase is removed before keyword rules so it is not counted twice.
* The reason is shown to the student, who can drag any slider. The student's own value always wins.
* If the latest Wellbeing check is High or Medium stress risk, the planner uses a lower effective energy (High -> at most 2, Medium -> at most 3), so the plan is gentler. A note says so.

## How the plan is built (plain code, no AI)
| Energy | Mode | Focus / break | Topics |
|---|---|---|---|
| 1-2 | low | 15 / 10 min | difficulty <= 2 only (harder ones "saved for later"; if all are hard, one gentle block) |
| 3 | normal | 20 / 5 min | easiest topic first (warm-up) |
| 4 | normal | 25 / 5 min | hardest topic first |
| 5 | high | 45 / 10 min | hardest topic first |

* A topic longer than one block is split into parts; the last part is shortened (min 10 min).
* No two hard blocks (difficulty >= 4) back to back when avoidable; easy/medium topics are finished in one run while enough light blocks remain to separate the hard ones.
* A long break (20-30 min) follows every 4th block; a 15-minute review closes sessions with 2+ topics.
* Limits: 15 topics, 80 characters each, 6 blocks per topic, 24 blocks per session; the time limit is respected.

## Safety and privacy
Nothing is stored by the planner (the plan lives on the page). Guest route is rate-limited per IP; the account route needs a login. No external service is contacted; the schedule is built by plain code on the server.

## Tests
`backend/tests/test_planner.py` (19 tests: ratings, modes, ordering, time limit, stress adjustment, input validation, routes) and 3 extra security-probe checks.
