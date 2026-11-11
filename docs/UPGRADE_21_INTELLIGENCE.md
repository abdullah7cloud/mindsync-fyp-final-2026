# Update 21 - intelligence evaluation (measured, with limits)

Everything below was produced by running `backend/scripts/intelligence_eval.py` against the running servers. The raw table is in
`docs/intelligence_results.md` (regenerated each run). Nothing here is typed in by hand, and nothing here proves the estimates are
*correct* for real students: they are design assumptions that are shown as ranges (see "Limits").

## What was compared

* **Current version** - the Update 21 task-aware engine plus the whole-plan scheduler, run through `/assist/understand` and `/assist/evaluate`.
* **Older version** - the Update 19 engine (`/demo/smart/plan`), started from the previous ZIP on another port and given the identical text,
  the same deadline, 120 study minutes per day and neutral answers (all optional questions skipped).

Ten realistic descriptions: a large and a small example of five kinds of work (programming, maths exam, research report, presentation, reading).

## Defects the evaluation found, and what was changed

| # | Defect found by running the ten cases | Change | Regression test |
|---|---|---|---|
| 1 | "calculus chapters **1 to 6**" was not counted, so a large maths exam (140 min) was estimated *smaller* than a short quiz (195 min) | numbered ranges after a unit ("chapters 1 to 6" = 6) and before it ("5 to 8 pages" = 6.5) are parsed | `test_numbered_ranges_and_minutes_are_counted_and_not_double_counted` |
| 2 | "**10 minute** presentation" had no unit, so a big group presentation (135 min) was estimated smaller than a 5-slide one (265 min) | talk minutes are a unit for presentations (24 min of preparation per minute of talk) | same test + `test_bigger_exam_and_presentation_are_estimated_bigger_than_small_ones` |
| 3 | "chapters 4 to 6 ... about 90 pages" was added together (chapters + pages) | for reading, exam and presentation the larger of the counts is used, they are not summed | same test |
| 4 | "due in 5 days" and "I have to ..." were treated as pieces of work | fragments that only say *when* are dropped and a leading "I have to" is stripped | `test_due_dates_are_not_counted_as_pieces_of_work`, `test_sentence_fragments_lose_their_leading_i_have_to` |
| 5 | "algebra quiz **tomorrow**" kept "tomorrow" in the title | day words end the title | `test_understand_drops_the_day_word_from_the_title` |
| 6 | "small" tasks were 40 % of a medium one; a small bug fix was 3 h 15 min | small = 30 % (about 2 h 20 min for programming) | covered by the ordering test |
| 7 | trivial tasks were marked *tight* when a bigger task shared their window | a task is *tight* only if it has no slack **and** uses at least half of its own window | `test_tight_status_is_for_tasks_that_really_use_their_window_not_trivial_ones` |
| 8 | 5-minute fragments ("Build it - 5 min") appeared at stage boundaries | a leftover under 10 minutes joins a neighbouring block of the same task and day | `test_no_useless_fragments_and_minutes_are_preserved` |
| 9 | splitting "login page **with** tests" into two items shrank a Python assignment from 480 to 180 min (an under-estimate, the harmful direction) | when the size is unknown, a short list of items cannot go below half of the usual effort for that kind of work | `test_a_short_list_does_not_shrink_an_unknown_size_task_below_half_of_the_usual_effort` |

## Measured result (same inputs, both versions)

| Type of work | Older: large vs small (min) | Current: large vs small (min) |
|---|---|---|
| Programming | 270 vs 195 - pass | 270 vs 140 - pass |
| Maths exam | **140 vs 195 - FAIL** | 360 vs 145 - pass |
| Research report | 1265 vs 210 - pass | 1265 vs 210 - pass |
| Presentation | **135 vs 265 - FAIL** | 235 vs 130 - pass |
| Reading | 320 vs 45 - pass | 320 vs 20 - pass |

So on these ten inputs the older version got the *ordering* of two of five pairs wrong and the current version got all five right. Everything else
in the table (programming-large, both reports, reading-large) is identical in the two versions, because the core of the engine was not changed.
That is an honest result: the improvement here is a set of fixes to counting and size handling, not a new model.

Different kinds of work receive different step sequences (programming: plan > build > fix > test > tidy; exam: understand > recall > practise >
review after a gap; report: research > outline > draft > references > edit; presentation: content > slides > rehearse aloud; reading: skim >
read > analyse). Five distinct sequences across the five kinds; a 20-minute article gets a single step. Session lengths follow the kind and the
difficulty (for example 10-35 minute blocks for presentations, 25-85 minute blocks for report writing) - see the table in `intelligence_results.md`.

### Several tasks together

Three tasks due in 3 days with 60 study minutes per day (measured with a throw-away comparison script in the working session):

* Older version: three separate plans, each one reporting its own shortfall (720, 255 and 300 min) as if it had the whole 180 minutes of capacity to itself. It cannot say that the three together do not fit.
* Current version: one plan, verdict **infeasible**, shortfall 1 280 minutes, every task marked *late*, with an "Ask for more time" alternative. Estimates were 895 / 245 / 360 min against 895 / 480 / 480 for the older version: the exam is now counted from "chapters 1 to 6" (6 chapters) and the Python assignment from its two listed items (with the half-of-usual floor). These two are judgement calls, not measured truths.
* Note: `UPGRADE_20_EVALUATION.md` quotes the older figures (895 / 480 / 480); they were true before this update and are kept there as history.

## Limits (state these in the viva)

* The minutes per unit, size multipliers and stage shares are the author's assumptions. They have **not** been validated against real students' logged times. The estimate is shown as a range (low - likely - high) and is corrected from the student's own history after sessions are completed (`taskaware/history.py`).
* Kind detection uses a word list. A task described with unusual words ("sort out the lab thing") is reported as *unknown*, which makes the app ask a question instead of guessing.
* A tiny fix still gets the five programming steps (some steps become short). It is not wrong but looks heavy for a one-line bug.
* The ten cases are a smoke test of behaviour, not a statistical evaluation. The usability study (SUS) and a comparison of estimated against actual minutes remain future work for the student's report.
* The optional external LLM never decides minutes. It can only widen the range, within 0.5x to 2x, and only after local validation.
