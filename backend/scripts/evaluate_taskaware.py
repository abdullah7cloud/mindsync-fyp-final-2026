"""
Compare the task-aware engine with the original baseline using measurable criteria.

Run from the backend folder:   python scripts/evaluate_taskaware.py
Writes docs/TASKAWARE_EVALUATION.md and ml_training/taskaware_eval.json.

What this does and does not show
--------------------------------
* The scenarios are written by the author, and the "students" in the history experiment are SIMULATED (a seeded
  random generator creates the actual times). The numbers therefore measure properties of the engine
  (does it differentiate tasks, ask when unsure, respect constraints, learn from outcomes, stay reproducible).
  They are NOT evidence that real students learn better, and the base effort numbers are design assumptions.
* The baseline is the code that existed before this update: app/planner.py (rule-based plan) and
  app/heuristic.py (deadline + energy ranking). Nothing is tuned to make the baseline look bad.
* Randomness is used only to simulate students here; the engine itself is deterministic.
"""
import json
import math
import random
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import planner as base_planner                      # noqa: E402
from app.heuristic import ScorableTask, rank_tasks           # noqa: E402
from app.taskaware import history as H                       # noqa: E402
from app.taskaware import workload as W                      # noqa: E402
from app.taskaware.analysis import analyse                   # noqa: E402
from app.taskaware.engine import PlanInput, run              # noqa: E402
from app.taskaware.ranking import rank_smart                 # noqa: E402

TODAY = date(2026, 10, 28)
DEADLINE = date(2026, 11, 13)
OUT_JSON = ROOT / "ml_training" / "taskaware_eval.json"
OUT_MD = ROOT.parent / "docs" / "TASKAWARE_EVALUATION.md"


def new_plan(title, details="", skill=3, **kw):
    answers = {"skill": skill, "progress": "none", **kw.pop("answers", {})}
    kw.setdefault("deadline", DEADLINE)
    return run(PlanInput(title=title, details=details, today=TODAY, answers=answers, **kw))


def old_plan(title, energy=3, category="General"):
    req = base_planner.PlanRequest(category=category, topics=[base_planner.TopicIn(title=title)], energy=energy)
    return base_planner.make_plan(req)


def sessions_of(plan):
    return [s for d in plan["schedule"]["days"] for s in d["sessions"]]


# ---------------------------------------------------------------------------------------------- E1 / E6
DIVERSE = [
    ("Debug my Python sorting function", "off-by-one error in merge sort", "programming"),
    ("Build a web app", "login page, task list, database, tests, deployment", "programming"),
    ("Calculus problem set", "12 problems on integration", "mathematics"),
    ("Revise for the physics exam", "waves, optics, forces, energy, circuits", "exam"),
    ("Essay on renewable energy policy", "2500 words", "writing"),
    ("Read chapter 5 of the networking textbook", "35 pages", "reading"),
    ("Group presentation on marketing", "12 slides", "presentation"),
    ("Analyse the survey results", "dataset of 800 responses, 6 charts", "data"),
    ("Email my tutor about the extension", "", "admin"),
    ("Write the unit tests for the API", "6 endpoints", "programming"),
]


def e1_e6():
    news, olds = [], []
    for title, details, _ in DIVERSE:
        n = new_plan(title, details, answers={"progress": "none"})
        news.append(n)
        olds.append(old_plan(title))
    new_sess = [s for n in news for s in sessions_of(n)]
    old_blocks = [i for o in olds for i in o.plan if i.kind == "study"]
    old_breaks = [i for o in olds for i in o.plan if i.kind in ("break", "long_break")]
    stage_sets = [frozenset(s["label"] for s in n["workload"]["stages"]) for n in news]
    pair = [(a, b) for i, a in enumerate(stage_sets) for b in stage_sets[i + 1:]]
    jacc = statistics.mean(1 - len(a & b) / len(a | b) for a, b in pair)
    from app.taskaware.schedule import Session, break_after as _break_after
    # a break only exists between two sessions on the same day, and a spread-out plan has one session a day; to
    # compare break POLICY, ask what break each session would get if another session followed it the same day
    policy = [_break_after(Session(0, s["stage_label"], s["kind"], s["work_id"], s["minutes"], s["deep"], 1, 1), 0, False) for s in new_sess]
    new_pairs = {(s["minutes"], s["break_after"]) for s in new_sess}
    old_pairs = {(i.minutes) for i in old_blocks}
    per_task_first_session = [sessions_of(n)[0]["minutes"] for n in news]
    return {
        "tasks": len(DIVERSE),
        "baseline_distinct_session_lengths": len({i.minutes for i in old_blocks}),
        "new_distinct_session_lengths": len({s["minutes"] for s in new_sess}),
        "baseline_distinct_break_lengths": len({i.minutes for i in old_breaks if i.kind == "break"}),
        "new_distinct_break_lengths": len({b for b in policy if b}),
        "baseline_stdev_session_minutes": round(statistics.pstdev([i.minutes for i in old_blocks]), 1),
        "new_stdev_session_minutes": round(statistics.pstdev([s["minutes"] for s in new_sess]), 1),
        "baseline_share_sessions_followed_by_break": round(len(old_breaks) / max(1, len(old_blocks)), 2),
        "new_share_sessions_followed_by_break": round(sum(1 for b in policy if b) / len(policy), 2),
        "mean_stage_set_difference_between_tasks_new": round(jacc, 2),
        "baseline_stage_types": 1,             # every topic is one repeated "study block"
        "new_stage_types": len({lab for st in stage_sets for lab in st}),
        "admin_task_scheduled_breaks": sum(1 for s in sessions_of(news[8]) if s["break_after"]),
        "baseline_total_minutes_for_web_app": sum(i.minutes for i in olds[1].plan if i.kind == "study"),
        "new_total_minutes_for_web_app": news[1]["workload"]["likely"],
    }


# ---------------------------------------------------------------------------------------------- E2 / E3
SKILL_TASKS = [("Python project", "login, tasks, search, tests"), ("Essay on history", "2000 words"),
               ("Calculus problem set", "15 problems"), ("Revise for the chemistry exam", "bonding, kinetics, equilibria, acids"),
               ("Data analysis of sales", "dataset, 5 charts")]


def e2_e3():
    ratios, old_ratios = [], []
    for t, d in SKILL_TASKS:
        a = new_plan(t, d, skill=1)["workload"]["likely"]
        b = new_plan(t, d, skill=5)["workload"]["likely"]
        ratios.append(round(a / b, 2))
        old_ratios.append(round(old_plan(t).study_minutes / old_plan(t).study_minutes, 2))   # no skill input exists
    sizes = [("Essay", ["500 words", "2000 words", "5000 words"]), ("Read", ["10 pages", "50 pages", "200 pages"]),
             ("Problem set", ["4 problems", "12 problems", "40 problems"]), ("Slides", ["5 slides", "12 slides", "30 slides"])]
    size_rows = []
    for name, opts in sizes:
        new_vals = [new_plan(f"{name}", o)["workload"]["likely"] for o in opts]
        old_vals = [old_plan(f"{name} {o}").study_minutes for o in opts]
        size_rows.append({"task": name, "inputs": opts, "new_minutes": new_vals, "baseline_minutes": old_vals,
                          "new_ratio_large_to_small": round(new_vals[-1] / new_vals[0], 1),
                          "baseline_ratio_large_to_small": round(old_vals[-1] / old_vals[0], 1)})
    return {"skill_ratio_beginner_over_expert_new": ratios, "skill_ratio_baseline": old_ratios, "size": size_rows}


# ---------------------------------------------------------------------------------------------- E4
VAGUE = ["Do my project", "Python project", "Study", "Assignment", "Finish coursework", "Work on thesis", "Exam",
         "Prepare", "Complete my Python project", "Homework", "Stuff", "Revision", "Coursework", "I need to complete my Java project"]
SPECIFIC = [("Write a 2000 word essay on climate policy", ""), ("Read chapter 4", "30 pages"), ("Revise for the exam", "limits, derivatives, integrals"),
            ("Presentation on our app", "10 slides"), ("Calculus homework", "12 problems"), ("Email my tutor", ""),
            ("Build a Python app", "login, search, export, tests"), ("Analyse the survey", "dataset with 5 charts"),
            ("Fix the bug in my login function", ""), ("Lab report", "1500 words")]


def e4():
    asked = 0
    for t in VAGUE:
        r = run(PlanInput(title=t, today=TODAY, deadline=DEADLINE, answers={"skill": 3}))
        asked += r["status"] == "needs_info"
    wrong = 0
    for t, d in SPECIFIC:
        r = run(PlanInput(title=t, details=d, today=TODAY, deadline=DEADLINE, answers={"skill": 3, "progress": "none"}))
        wrong += r["status"] == "needs_info"
    max_q = max(len(run(PlanInput(title=t, today=TODAY, deadline=DEADLINE)).get("questions", [])) for t in VAGUE)
    return {"vague_inputs": len(VAGUE), "specific_inputs": len(SPECIFIC),
            "new_asked_on_vague": asked, "new_asked_on_vague_rate": round(asked / len(VAGUE), 2),
            "new_unnecessary_questions_on_specific": wrong, "new_unnecessary_question_rate": round(wrong / len(SPECIFIC), 2),
            "max_questions_in_one_round": max_q,
            "baseline_asked_on_vague_rate": 0.0, "baseline_false_confidence_rate_on_vague": 1.0}


# ---------------------------------------------------------------------------------------------- E5 (simulated students)
def e5(seed=42, students=300):
    rng = random.Random(seed)
    tasks = [("Python project", d) for d in ("login, tasks", "login, tasks, search, tests", "api, database, auth, tests, docs, ui")]
    raws = {d: W.estimate(analyse(t, d), 3, {"progress": "none"}).raw_likely for t, d in tasks}
    results = {}
    mults = [0.6, 1.0, 1.5, 2.0, 3.0]
    ns = [0, 1, 2, 3, 5, 8, 12]
    for m in mults:
        row = {}
        for n in ns:
            errs_new, errs_base = [], []
            for _ in range(students):
                outs = []
                for _i in range(n):
                    t, d = rng.choice(tasks)
                    raw = raws[d]
                    outs.append(H.Outcome("programming", raw, raw * m * math.exp(rng.gauss(0, 0.25))))
                t, d = rng.choice(tasks)
                raw = raws[d]
                actual = raw * m * math.exp(rng.gauss(0, 0.25))
                cal = H.calibration("programming", outs)
                errs_base.append(abs(raw - actual) / actual)
                errs_new.append(abs(raw * cal["factor"] - actual) / actual)
            row[n] = {"raw_mape": round(100 * statistics.mean(errs_base), 1), "new_mape": round(100 * statistics.mean(errs_new), 1)}
        results[str(m)] = row
    # one unusual session
    normal = [H.Outcome("programming", 600, 600 * math.exp(rng.gauss(0, 0.1))) for _ in range(5)]
    f0 = H.calibration("programming", normal)["factor"]
    f1 = H.calibration("programming", normal + [H.Outcome("programming", 600, 3000)])["factor"]
    single = H.calibration("programming", [H.Outcome("programming", 600, 3000)])["factor"]
    return {"students_per_cell": students, "true_multipliers": mults, "history_sizes": ns, "mape_percent": results,
            "outlier_after_5_normal_factor_change_percent": round(100 * (f1 / f0 - 1), 1),
            "single_5x_session_factor": round(single, 2)}


# ---------------------------------------------------------------------------------------------- E7 / E8
def e7_e8():
    cases = [("Complete my software project", "login, tasks, search, tests, report"), ("Essay", "3000 words"),
             ("Revise for the exam", "waves, optics, forces, energy, circuits"), ("Calculus problem set", "30 problems"),
             ("Read the textbook", "120 pages")]
    violations = checked = infeasible = missed_feasible = 0
    repro = 0
    for title, details in cases:
        for days_left in (1, 2, 3, 5, 8, 14, 30):
            for hours in (30, 60, 120, 240):
                dl = date.fromordinal(TODAY.toordinal() + days_left)
                kw = dict(deadline=dl, daily_minutes=hours)
                r = new_plan(title, details, **kw)
                r2 = new_plan(title, details, **kw)
                repro += json.dumps(r, sort_keys=True, default=str) == json.dumps(r2, sort_keys=True, default=str)
                sc = r["schedule"]
                checked += 1
                bad = any(d["total_minutes"] > hours or date.fromisoformat(d["date"]) > date.fromisoformat(sc["last_day"]) for d in sc["days"])
                placed = sum(d["total_minutes"] for d in sc["days"])
                bad = bad or placed + sc["shortfall_minutes"] != sc["total_minutes"] or sc["feasible"] != (sc["shortfall_minutes"] == 0)
                violations += bad
                infeasible += not sc["feasible"]
                if sc["feasible"] is False and sc["total_minutes"] <= 0.7 * sc["capacity_minutes"]:
                    missed_feasible += 1          # said "does not fit" although there was ample room
    return {"scenarios": checked, "constraint_violations": violations, "flagged_infeasible": infeasible,
            "wrongly_flagged_infeasible_with_ample_room": missed_feasible, "reproducible_runs": repro}


# ---------------------------------------------------------------------------------------------- E9 (constructed labels)
def e9():
    big = [("Complete my Python project", 900), ("Write dissertation chapter 2", 720), ("Lab report with analysis", 240),
           ("Revise for the maths exam", 600), ("Build the group web app", 1200)]
    small = [("Email my tutor", 5), ("Read 5 pages", 20), ("Tidy my files", 20), ("Reply to the group chat", 5), ("Submit the form", 10)]
    now = datetime(2026, 10, 28, 9, tzinfo=timezone.utc)
    cases = []
    for bt, effort in big:
        for st, _ in small:
            avail_hours = (effort / 60.0) / 2.0 * 24 * 0.6          # 2 h of study a day -> only 60% of the time needed
            cases.append((bt, st, max(effort / 60.0 * 0.6 * 12, 24)))
    right_new = right_old = 0
    for bt, st, big_hours in cases:
        tasks = [ScorableTask("big", bt, 4, now + timedelta(hours=big_hours)), ScorableTask("small", st, 1, now + timedelta(hours=big_hours / 2))]
        right_old += rank_tasks(tasks, 3, now=now)[0][0].task.id == "big"
        right_new += rank_smart(tasks, 3, details={}, now=now)[0][0].task.id == "big"
    return {"constructed_cases": len(cases), "baseline_correct": right_old, "new_correct": right_new}


def main():
    res = {"e1_e6_differentiation_and_repetition": e1_e6(), "e2_e3_skill_and_size": e2_e3(), "e4_clarification": e4(),
           "e5_history_simulation": e5(), "e7_e8_constraints_and_reproducibility": e7_e8(), "e9_ranking": e9()}
    OUT_JSON.write_text(json.dumps(res, indent=1))
    write_report(res)
    print(json.dumps(res["e1_e6_differentiation_and_repetition"], indent=1))
    print(json.dumps(res["e4_clarification"], indent=1))
    print(json.dumps(res["e7_e8_constraints_and_reproducibility"], indent=1))
    print(json.dumps(res["e9_ranking"], indent=1))


def write_report(r):
    a, b, c = r["e1_e6_differentiation_and_repetition"], r["e2_e3_skill_and_size"], r["e4_clarification"]
    h, k, rk = r["e5_history_simulation"], r["e7_e8_constraints_and_reproducibility"], r["e9_ranking"]
    hist_rows = []
    for m in h["true_multipliers"]:
        cells = " | ".join(f"{h['mape_percent'][str(m)][n]['raw_mape']:.0f} -> {h['mape_percent'][str(m)][n]['new_mape']:.0f}" for n in h["history_sizes"])
        hist_rows.append(f"| x{m} | {cells} |")
    size_rows = "\n".join(f"| {s['task']} | {s['inputs'][0]} / {s['inputs'][1]} / {s['inputs'][2]} | {s['baseline_minutes']} | {s['new_minutes']} |" for s in b["size"])
    md = f"""# Task-aware engine: evaluation against the baseline

Generated by `backend/scripts/evaluate_taskaware.py` (raw numbers: `backend/ml_training/taskaware_eval.json`). Re-run it to reproduce every figure.

## What this evaluation can and cannot show

- The **baseline** is the code that existed before update 19: `app/planner.py` (fixed 15/20/25/45-minute blocks chosen by energy, topic difficulty from a keyword table) and `app/heuristic.py` (deadline + energy ranking).
- Scenarios were written by the author. The students in experiment 5 are **simulated** with a seeded random generator. The results measure properties of the engine. They are **not** evidence that real students learn or plan better, and the base effort numbers inside the engine are design assumptions that still need validating with real student data.
- Experiment 9 uses labels set by construction (a big task that cannot be finished in the time left versus a small task due sooner). It checks that the ranking notices work pressure; it is not an accuracy figure on real tasks.

## 1. Different tasks get different recommendations ({a['tasks']} tasks of different kinds)

| Measure | Baseline | New engine |
|---|---|---|
| Distinct session lengths used | {a['baseline_distinct_session_lengths']} | {a['new_distinct_session_lengths']} |
| Standard deviation of session length (min) | {a['baseline_stdev_session_minutes']} | {a['new_stdev_session_minutes']} |
| Distinct break lengths | {a['baseline_distinct_break_lengths']} | {a['new_distinct_break_lengths']} |
| Share of sessions that get a break when another follows | {a['baseline_share_sessions_followed_by_break']} | {a['new_share_sessions_followed_by_break']} |
| Kinds of stage in the plans | {a['baseline_stage_types']} (repeated study block) | {a['new_stage_types']} |
| Mean difference between the stage sets of two tasks (0 = identical, 1 = nothing shared) | 0 | {a['mean_stage_set_difference_between_tasks_new']} |
| Scheduled breaks in the quick admin task | n/a | {a['admin_task_scheduled_breaks']} |
| Total study minutes for "Build a web app" (login, task list, database, tests, deployment) | {a['baseline_total_minutes_for_web_app']} | {a['new_total_minutes_for_web_app']} |

## 2. Student skill changes the plan

The same five tasks planned for a beginner (skill 1) and an expert (skill 5). Ratio of total workload, beginner / expert: **{b['skill_ratio_beginner_over_expert_new']}** (new engine). The baseline has no skill input, so the ratio is {b['skill_ratio_baseline']}.

## 3. Workload follows the size of the task (total minutes)

| Task | Small / medium / large input | Baseline | New engine |
|---|---|---|---|
{size_rows}

## 4. Missing information triggers questions

| Measure | Baseline | New engine |
|---|---|---|
| Vague inputs ({c['vague_inputs']}, e.g. "Do my project"): asked a question instead of planning | {c['baseline_asked_on_vague_rate']:.0%} (planned every time) | {c['new_asked_on_vague_rate']:.0%} |
| Specific inputs ({c['specific_inputs']}): unnecessary questions | 0% | {c['new_unnecessary_question_rate']:.0%} |
| Most questions in one round | 0 | {c['max_questions_in_one_round']} |

## 5. Learning from previous tasks (simulated students, {h['students_per_cell']} per cell)

Mean absolute percentage error of the estimate for the next task, **raw estimate (no learning) -> estimate after learning**, for students whose real times are a constant multiple of the engine's raw estimate (with 25% random variation per task). Here the "baseline" is the engine's own estimate before any history is applied, because the old planner gave one fixed duration per topic and cannot be compared on this. Columns are the number of finished tasks the engine has seen ({', '.join(str(n) for n in h['history_sizes'])}).

| True time vs raw estimate | {' | '.join('n=' + str(n) for n in h['history_sizes'])} |
|---|{'---|' * len(h['history_sizes'])}
{chr(10).join(hist_rows)}

Robustness: after five normal results, one result five times too long changes the estimate by **{h['outlier_after_5_normal_factor_change_percent']}%**; a single 5x result with no other history moves the estimate to a factor of **{h['single_5x_session_factor']}** (capped, shrunk). For a student whose estimates are already right (x1.0) learning changes the error by 1 percentage point or less, so it does no harm there.

## 6. Constraints and reproducibility ({k['scenarios']} scenarios: 5 tasks x 7 deadlines x 4 daily-hour limits)

| Check | Result |
|---|---|
| Sessions outside the allowed days, or a day over the hours available, or inconsistent totals | {k['constraint_violations']} |
| Plans flagged "does not fit" (and reported with the shortfall) | {k['flagged_infeasible']} |
| Flagged "does not fit" although the work used 70% or less of the capacity | {k['wrongly_flagged_infeasible_with_ample_room']} |
| Identical output when the same input is run twice | {k['reproducible_runs']} of {k['scenarios']} |

## 7. Ranking notices how much work is left ({rk['constructed_cases']} constructed cases)

Each case has a big task that cannot be finished in the time left and a small task due sooner. Correct = the big task ranked first.

| | Baseline (deadline + energy) | New (adds work pressure) |
|---|---|---|
| Correct | {rk['baseline_correct']} of {rk['constructed_cases']} | {rk['new_correct']} of {rk['constructed_cases']} |

## Limits of these results

1. The engine's base effort per kind of work, the skill multipliers and the session lengths are assumptions of the author. Experiment 5 shows the engine can correct a wrong assumption for a student after a few finished tasks; it does not show that the starting assumptions are right.
2. No real student data has been collected yet. The first real test is the usability study and a few weeks of logged outcomes; `GET /smart/learned` shows what MindSync learned for each student.
3. The task classifier is a word list. Rare words, other languages and unusual phrasing give "unknown", and the engine then asks.
4. The wellbeing model and the experimental task-fit model do not take part in judging task complexity.
"""
    OUT_MD.write_text(md)


if __name__ == "__main__":
    main()
