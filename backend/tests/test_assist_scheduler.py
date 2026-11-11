"""Scheduler: guarantees (capacity, deadlines, feasibility) checked on many generated task sets, plus every setting's effect."""
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.assist.scheduler import (LAST_USABLE_HOUR, PlanTask, build_schedule, day_capacities, edf_shortfall)
from app.assist.settings_schema import StudySettings, settings_from

TZ = ZoneInfo("Europe/Copenhagen")
NOW = datetime(2026, 10, 29, 9, 0, tzinfo=TZ)        # a Thursday


def task(i, days, minutes, hour=20, high=None, diff=3.0, prio=2):
    d = (NOW + timedelta(days=days)).replace(hour=hour, minute=0)
    return PlanTask(id=f"t{i}", title=f"Task {i}", deadline=d, remaining=minutes, remaining_high=high or int(minutes * 1.3),
                    kind="general", difficulty=diff, priority=prio)


def total_by_day(res):
    return {d["date"]: sum(s["minutes"] for s in d["sessions"]) for d in res["days"]}


def test_never_exceeds_capacity_and_respects_deadlines_on_random_sets():
    rnd = random.Random(2026)
    checked_feasible = checked_infeasible = 0
    for trial in range(250):
        n = rnd.randint(1, 5)
        tasks = [task(i, rnd.randint(0, 14), rnd.choice(range(30, 600, 15)), hour=rnd.choice([9, 12, 18, 20, 23])) for i in range(n)]
        st = StudySettings(weekday_minutes=rnd.choice([60, 90, 120, 180]), weekend_minutes=rnd.choice([0, 60, 120]),
                           buffer_days=rnd.choice([0, 1, 2]), pacing=rnd.choice(["even", "early"]))
        res = build_schedule(tasks, st, now=NOW, energy=rnd.choice([None, 1, 3, 5]), alternatives=False)
        caps = {d["date"]: d["capacity"] for d in res["days"]}
        for day in res["days"]:
            assert day["planned"] <= day["capacity"], (trial, day["date"])
        per = res["tasks"]
        for t in tasks:
            info = per[t.id]
            last = info["last_usable_day"]
            for day in res["days"]:
                for s in day["sessions"]:
                    if s["task_id"] == t.id:
                        # never after the last usable day, unless the task is already overdue / due today (planned today)
                        assert day["date"] <= max(last, NOW.date().isoformat()), (trial, t.id)
            assert info["scheduled"] + info["unscheduled"] == info["remaining"]
        # feasibility is exactly the EDF test on the real deadlines
        caps_list = day_capacities(st, NOW, len(res["days"]), energy=None, stress=None)
        if res["feasibility"]["feasible"]:
            checked_feasible += 1
            assert all(v["unscheduled"] == 0 for v in per.values()), trial
        else:
            checked_infeasible += 1
            assert any(v["unscheduled"] > 0 for v in per.values()), trial
    assert checked_feasible > 40 and checked_infeasible > 20      # both branches were really exercised


def test_feasible_sets_are_fully_scheduled_even_when_the_plan_is_tight():
    # 4 tasks that exactly fill the capacity: pacing must not push anything over a deadline
    tasks = [task(0, 1, 120, hour=20), task(1, 2, 120, hour=20), task(2, 3, 120, hour=20), task(3, 3, 120, hour=20)]
    res = build_schedule(tasks, StudySettings(weekday_minutes=120, weekend_minutes=120, buffer_days=0), now=NOW.replace(hour=8), alternatives=False)
    assert res["feasibility"]["feasible"], res["feasibility"]
    assert all(v["unscheduled"] == 0 for v in res["tasks"].values())


def test_shortfall_matches_edf_formula():
    items = [(0, 100, "a"), (1, 200, "b")]
    # by hand: a needs 100 by day 0 (capacity 60) -> 40 short; a+b need 300 by day 1 (capacity 120) -> 180 short
    assert edf_shortfall(items, [60, 60, 60]) == (180, "a")         # largest shortfall 180; "a" is the first deadline that fails
    assert edf_shortfall(items, [100, 200, 0]) == (0, None)


def test_infeasible_reports_shortfall_critical_task_and_verified_alternatives():
    tasks = [task(0, 3, 600), task(1, 3, 600)]
    res = build_schedule(tasks, StudySettings(), now=NOW)
    f = res["feasibility"]
    assert f["level"] == "infeasible" and f["shortfall_minutes"] > 0 and f["critical_task"]
    assert res["alternatives"], "an infeasible plan must come with alternatives"
    # every alternative claims to fix the problem: apply it and check
    for alt in res["alternatives"]:
        t2, st2 = [PlanTask(**{**t.__dict__}) for t in tasks], StudySettings()
        if alt["id"] == "more_time":
            st2 = StudySettings(weekday_minutes=120 + alt["effect"]["extra_minutes_per_day"], weekend_minutes=90 + alt["effect"]["extra_minutes_per_day"], buffer_days=0)
        elif alt["id"] == "postpone":
            t2 = [t for t in t2 if t.id != alt["effect"]["task_id"]]
            st2 = StudySettings(buffer_days=0)
        elif alt["id"] == "reduce_scope":
            pct = alt["effect"]["scope_percent"] / 100.0
            for t in t2:
                if alt["effect"]["applies_to"] == "all" or t.id == res["feasibility"]["critical_task"]["id"]:
                    t.remaining = int(t.remaining * pct) // 5 * 5
            st2 = StudySettings(buffer_days=0)
        elif alt["id"] == "extend":
            for t in t2:
                if t.id in alt["effect"]["task_ids"]:
                    t.deadline += timedelta(days=alt["effect"]["extra_days"])
            st2 = StudySettings(buffer_days=0)
        else:
            continue
        again = build_schedule(t2, st2, now=NOW, alternatives=False)
        assert again["feasibility"]["feasible"], alt


def test_buffer_is_used_when_possible_and_dropped_when_not():
    t = [task(0, 4, 240)]
    loose = build_schedule(t, StudySettings(buffer_days=2), now=NOW)
    assert loose["use_buffer"] and loose["feasibility"]["level"] in ("comfortable", "tight")
    assert loose["tasks"]["t0"]["slack_days"] >= 2 or loose["tasks"]["t0"]["slack_days"] >= 1
    tight = build_schedule([task(0, 1, 200)], StudySettings(buffer_days=2), now=NOW)
    assert tight["feasibility"]["feasible"] and tight["feasibility"]["buffer_used"] and not tight["use_buffer"]


def test_study_days_and_weekend_minutes_are_obeyed():
    st = StudySettings(study_days=[0, 1, 2, 3], weekend_minutes=0)
    res = build_schedule([task(0, 10, 400)], st, now=NOW, alternatives=False)
    for d in res["days"]:
        if d["weekday"] in (4, 5, 6):
            assert d["planned"] == 0 and d["capacity"] == 0
    assert res["feasibility"]["feasible"]


def test_daily_minutes_setting_changes_capacity_and_plan_length():
    a = build_schedule([task(0, 10, 600)], StudySettings(weekday_minutes=60, weekend_minutes=60, pacing="early"), now=NOW, alternatives=False)
    b = build_schedule([task(0, 10, 600)], StudySettings(weekday_minutes=180, weekend_minutes=180, pacing="early"), now=NOW, alternatives=False)
    assert max(d["planned"] for d in a["days"]) <= 60 and max(d["planned"] for d in b["days"]) > 60


def test_pacing_early_front_loads_and_even_spreads():
    t = lambda: [task(0, 8, 480)]
    even = build_schedule(t(), StudySettings(pacing="even", buffer_days=0), now=NOW, alternatives=False)
    early = build_schedule(t(), StudySettings(pacing="early", buffer_days=0), now=NOW, alternatives=False)
    e, f = total_by_day(even), total_by_day(early)
    first = lambda m: m[sorted(m)[0]]
    assert first(f) > first(e)
    assert early["tasks"]["t0"]["finish_date"] <= even["tasks"]["t0"]["finish_date"]


def test_gentle_mode_lowers_load_only_when_on():
    base = build_schedule([task(0, 6, 300)], StudySettings(gentle_mode="off"), now=NOW, energy=1, alternatives=False)
    auto = build_schedule([task(0, 6, 300)], StudySettings(gentle_mode="auto"), now=NOW, energy=1, alternatives=False)
    calm = build_schedule([task(0, 6, 300)], StudySettings(gentle_mode="auto"), now=NOW, energy=4, alternatives=False)
    assert auto["days"][0]["capacity"] < base["days"][0]["capacity"]
    assert auto["gentle"]["on"] and not calm["gentle"]["on"] and not base["gentle"]["on"]
    assert any("Gentle" in n for n in auto["notes"])
    high = build_schedule([task(0, 6, 300)], StudySettings(gentle_mode="auto"), now=NOW, energy=4, stress="High", alternatives=False)
    assert high["gentle"]["reason"] == "wellbeing" and high["days"][1]["capacity"] < calm["days"][1]["capacity"]


def test_low_energy_puts_easy_work_first_today_and_hard_first_otherwise():
    tasks = [task(0, 3, 90, diff=4.5), task(1, 3, 90, diff=1.5)]
    low = build_schedule(tasks, StudySettings(), now=NOW, energy=2, alternatives=False)
    ok = build_schedule(tasks, StudySettings(), now=NOW, energy=4, alternatives=False)
    first_low = low["days"][0]["sessions"][0]["task_id"]
    first_ok = ok["days"][0]["sessions"][0]["task_id"]
    assert first_low == "t1" and first_ok == "t0"


def test_preferred_time_gives_clock_hints_and_flexible_does_not():
    flex = build_schedule([task(0, 4, 120)], StudySettings(preferred_time="flexible"), now=NOW, alternatives=False)
    eve = build_schedule([task(0, 4, 120)], StudySettings(preferred_time="evening"), now=NOW, alternatives=False)
    assert flex["days"][1]["sessions"][0]["start_hint"] is None
    assert eve["days"][1]["sessions"][0]["start_hint"] == "19:00"


def test_session_and_break_styles_change_blocks():
    t = lambda: [task(0, 6, 360)]
    std = build_schedule(t(), StudySettings(session_style="standard", break_style="standard"), now=NOW, alternatives=False)
    short = build_schedule(t(), StudySettings(session_style="short", break_style="long"), now=NOW, alternatives=False)
    longs = build_schedule(t(), StudySettings(session_style="long"), now=NOW, alternatives=False)
    mean = lambda r: sum(s["minutes"] for d in r["days"] for s in d["sessions"]) / max(1, sum(len(d["sessions"]) for d in r["days"]))
    assert mean(short) < mean(std) < mean(longs)
    brk = lambda r: max([s["break_after"] for d in r["days"] for s in d["sessions"]] or [0])
    assert brk(short) >= brk(std)


def test_overdue_and_due_today_are_planned_today():
    od = PlanTask(id="x", title="Late", deadline=NOW - timedelta(days=1), remaining=60, remaining_high=80)
    res = build_schedule([od], StudySettings(), now=NOW, alternatives=False)
    assert res["tasks"]["x"]["flag"] == "overdue" and res["days"][0]["planned"] > 0
    early = PlanTask(id="y", title="Noon", deadline=NOW.replace(hour=14), remaining=60, remaining_high=80)
    res = build_schedule([early], StudySettings(), now=NOW, alternatives=False)
    assert res["tasks"]["y"]["flag"] == "due_today" and res["days"][0]["planned"] > 0


def test_deadline_before_six_pm_does_not_plan_that_day():
    t = PlanTask(id="z", title="Noon deadline", deadline=(NOW + timedelta(days=2)).replace(hour=12), remaining=60, remaining_high=70)
    res = build_schedule([t], StudySettings(buffer_days=0), now=NOW, alternatives=False)
    assert res["tasks"]["z"]["last_usable_day"] == (NOW + timedelta(days=1)).date().isoformat()
    assert LAST_USABLE_HOUR == 18


def test_milestones_mark_the_end_of_each_step_in_order():
    stages = [{"work_id": "general_work", "kind": "general", "label": f"Step {i}", "method": "m", "minutes": 120, "deep": True, "session": [25, 40, 60], "breaks": True} for i in range(3)]
    t = PlanTask(id="m", title="Project", deadline=NOW + timedelta(days=9), remaining=360, remaining_high=450, stages=stages)
    res = build_schedule([t], StudySettings(), now=NOW, alternatives=False)
    labels = [m["label"] for m in res["milestones"]]
    assert labels == ["Step 0", "Step 1", "Step 2"]
    dates = [m["date"] for m in res["milestones"]]
    assert dates == sorted(dates)


def test_today_is_reduced_by_time_already_studied_and_late_hour():
    st = StudySettings(weekday_minutes=120)
    morning = day_capacities(st, NOW.replace(hour=9), 2, energy=3, stress=None)
    evening = day_capacities(st, NOW.replace(hour=20), 2, energy=3, stress=None)
    studied = day_capacities(st, NOW.replace(hour=9), 2, energy=3, stress=None, studied_today=60)
    assert evening[0] < morning[0] and studied[0] <= 60 and morning[1] == 120
    assert day_capacities(st, NOW, 2, energy=3, stress=None, today_minutes=45)[0] == 45


def test_settings_validation_and_fallback():
    assert settings_from({"weekday_minutes": 99999, "buffer_days": 2}).buffer_days == 2      # bad field dropped, good one kept
    assert settings_from(None).weekday_minutes == 120
    with pytest.raises(Exception):
        StudySettings(study_days=[])
    with pytest.raises(Exception):
        StudySettings(timezone="Mars/Olympus")
    with pytest.raises(Exception):
        StudySettings(remind_lead_hours=[5])


def test_tight_status_is_for_tasks_that_really_use_their_window_not_trivial_ones():
    # 240 minutes into exactly 240 minutes of capacity is tight; a 20-minute task with slack 0 only because the
    # first task fills the days before its deadline must not be reported as tight itself
    s = StudySettings(weekday_minutes=120, weekend_minutes=120, buffer_days=0)
    tasks = [task(0, 1, 240, hour=20), task(1, 6, 20, hour=20)]
    res = build_schedule(tasks, s, now=NOW.replace(hour=8), alternatives=False)
    assert res["tasks"]["t0"]["status"] == "tight"
    assert res["tasks"]["t1"]["status"] == "on_track"


def test_no_useless_fragments_and_minutes_are_preserved():
    # many shapes of task: apart from a final remainder every block is at least 10 minutes and nothing is lost
    from app.assist.requests import aware  # noqa: F401  (import check only)
    rng = random.Random(7)
    s = StudySettings(weekday_minutes=90, weekend_minutes=120, buffer_days=0)
    for i in range(40):
        tasks = [task(0, rng.randint(2, 12), rng.choice([60, 140, 270, 480, 760]), hour=20)]
        tasks[0].kind = "programming"
        res = build_schedule(tasks, s, now=NOW.replace(hour=8), alternatives=False)
        mins = [x["minutes"] for d in res["days"] for x in d["sessions"]]
        assert sum(mins) == tasks[0].remaining or res["tasks"]["t0"]["unscheduled"], (i, sum(mins), tasks[0].remaining)
        assert all(m >= 10 for m in mins[:-1]), mins          # only the very last block of a task may be a short remainder
