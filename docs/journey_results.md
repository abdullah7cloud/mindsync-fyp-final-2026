# Journey probe results (measured)

Run 2026-10-29 against http://localhost:8000: 48 / 48 checks passed.

| Check | Result | Detail |
|---|---|---|
| register | PASS | 201 |
| understand finds three tasks | PASS | ['Stats exam', '1500 word report', 'Read a 12 page article'] |
| understand never leaves a day word in a title | PASS |  |
| evaluate returns a verdict and per-task estimates | PASS | tight |
| evaluate saved nothing | PASS |  |
| accept saves tasks and a plan | PASS |  |
| a plan with sessions for today exists | PASS | 4 blocks today |
| low energy is reflected | PASS |  |
| low energy offers a replan | PASS | ['energy'] |
| replan applies | PASS | 200 |
| today is lighter or equal after low energy | PASS | 50 vs 120 min |
| no task became infeasible | PASS | tight |
| a finished block is saved | PASS | 201 |
| an early stop is saved and says what it learned | PASS |  |
| dashboard counts the 35 minutes studied and 2 sessions | PASS | 35 min, 2 sessions |
| dashboard totals show three pending tasks | PASS | 3 |
| dashboard has no error text | PASS |  |
| a smaller study day triggers a replan offer or an infeasible/tight verdict | PASS | tight |
| after replan no future day exceeds the new daily limit | PASS |  |
| assistant answers and says who wrote it | PASS | local |
| prompt-injection question gets a safe planner answer | PASS |  |
| weekly review works | PASS | 200 |
| a task can be completed | PASS |  |
| a task can be re-opened | PASS |  |
| reminder history is readable | PASS |  |
| notification status is readable | PASS | outbox |
| usage endpoint never shows a key | PASS |  |
| the WHOLE roadmap is saved in the database (every planned block is listed in My Tasks) | PASS | 35 saved, 35 in the plan |
| My Tasks shows Day N of total | PASS | day 1 of 10 |
| a block to confirm exists | PASS |  |
| confirming Done is saved | PASS | 200 |
| My Tasks progress counts only what was confirmed | PASS | done 1, 20 min |
| the Dashboard updates from the confirmation (+20 minutes) | PASS | 35 -> 55 |
| the confirmed block is in the Completed list | PASS |  |
| a new plan keeps the confirmed block and its minutes (history preserved) | PASS |  |
| the replan preview says what is kept and replaced, and changes nothing | PASS |  |
| Delayed moves a block to tomorrow and remembers where it was | PASS |  |
| an answer can be undone | PASS |  |
| the student can add their own block | PASS | 201 |
| daily and deadline reminders exist, appear in the app only, and say so | PASS | 3 reminders |
| reminders are not duplicated by reloading | PASS |  |
| the sample Learning Pack opens without AI | PASS |  |
| a quiz is marked on the server with explanations | PASS |  |
| the Dashboard shows the real quiz result | PASS |  |
| making a pack from own text says AI is not switched on (nothing faked, nothing paid) | PASS | 409 |
| profile is readable | PASS |  |
| guest understand works without an account | PASS |  |
| guest evaluate works | PASS | 200 |
