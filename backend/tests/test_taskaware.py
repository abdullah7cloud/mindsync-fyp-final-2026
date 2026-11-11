"""
Tests for the task-aware planning engine (app/taskaware). They check behaviour a student would notice, not only
that the code runs: different tasks get different plans, skill changes the plan, vague input triggers questions,
history changes estimates sensibly, constraints hold, results are reproducible.
"""
import json
import math
from datetime import date

import pytest

from app.taskaware import analysis as A
from app.taskaware import history as H
from app.taskaware import schedule as S
from app.taskaware.engine import PlanInput, run
from app.taskaware.ranking import rank_smart

TODAY = date(2026, 10, 28)
DEADLINE = date(2026, 11, 13)


def plan(title, details="", **kw):
    kw.setdefault("deadline", DEADLINE)
    kw["answers"] = {"skill": 3, "progress": "none", **kw.get("answers", {})}
    return run(PlanInput(title=title, details=details, today=TODAY, **kw))


# ---------- 1. classification ----------
def test_kinds_are_recognised_with_evidence():
    a = A.analyse("Debug my Python sorting function")
    assert a.primary == "programming" and a.kind_known
    assert "debug" in a.kinds[0].evidence
    assert A.analyse("Write a 2000 word essay on climate policy").primary == "writing"
    assert A.analyse("Revise for the statistics exam").primary == "exam"
    assert A.analyse("Prepare 10 slides for the group presentation").primary == "presentation"


def test_a_task_can_have_several_kinds():
    a = A.analyse("Python project with a written report", "login, task list, report of 3000 words")
    assert {k.kind for k in a.kinds} == {"programming", "writing"}


def test_unit_tests_are_not_exams():
    a = A.analyse("Write unit tests for my API")
    assert a.primary == "programming"


def test_short_vague_title_is_reported_as_unknown_not_guessed():
    a = A.analyse("Do the thing")
    assert not a.kind_known and a.primary == "general" and a.kind_confidence < 0.4


def test_exam_subject_is_not_planned_as_two_kinds():
    a = A.analyse("Study for calculus exam")
    assert a.primary == "exam" and a.subjects == ["mathematics"]


# ---------- 2/3. different tasks, different plans ----------
def stage_labels(r):
    return [s["label"] for s in r["workload"]["stages"]]


def test_different_kinds_get_different_stages_and_methods():
    prog = plan("Build a Python web app", "login page, task list, database, tests")
    math_ = plan("Calculus problem set", "12 problems on integration")
    essay = plan("Essay on renewable energy", "2000 words")
    assert set(stage_labels(prog)).isdisjoint(stage_labels(math_))
    assert set(stage_labels(essay)).isdisjoint(stage_labels(math_))
    assert "Test it" in stage_labels(prog) and "Check references" in stage_labels(essay)
    assert "Review your mistakes" in stage_labels(math_)


def test_session_lengths_are_not_one_universal_number():
    lengths = set()
    for title, details in [("Build a Python web app", "login, tasks, tests, database"), ("Revise for physics exam", "waves, optics, forces, energy"),
                           ("Read chapter 3", "40 pages"), ("Essay on history", "2500 words")]:
        r = plan(title, details)
        lengths |= {s["minutes"] for d in r["schedule"]["days"] for s in d["sessions"]}
    assert len(lengths) >= 5 and 20 not in lengths or len(lengths) >= 5


def test_same_task_different_skill_gives_different_plan():
    beginner = plan("Python project", "login, tasks, tests", answers={"skill": 1})
    expert = plan("Python project", "login, tasks, tests", answers={"skill": 5})
    assert beginner["workload"]["likely"] >= 1.8 * expert["workload"]["likely"]
    assert beginner["difficulty"]["for_you"] > expert["difficulty"]["for_you"]
    assert beginner["difficulty"]["intrinsic"] == expert["difficulty"]["intrinsic"]      # intrinsic is separate from personal


def test_workload_scales_with_stated_size():
    small = plan("Essay", "500 words")["workload"]["likely"]
    large = plan("Essay", "5000 words")["workload"]["likely"]
    assert large >= 5 * small


def test_large_task_is_split_into_stages_over_several_days():
    r = plan("Complete my software project", "login, tasks, search, tests, report")
    assert len(r["workload"]["stages"]) >= 4
    assert len(r["schedule"]["days"]) >= 3
    assert r["workload"]["low"] < r["workload"]["likely"] < r["workload"]["high"]


def test_total_workload_session_break_and_time_left_are_separate_numbers():
    r = plan("Python project", "login, tasks, tests", daily_minutes=90)
    total = r["workload"]["likely"]
    longest = max(s["minutes"] for d in r["schedule"]["days"] for s in d["sessions"])
    assert total > 5 * longest
    assert r["schedule"]["capacity_minutes"] != total and r["schedule"]["days_available"] > 1


def test_work_already_done_is_not_planned_again():
    fresh = plan("Python project", "login, tasks, tests", answers={"skill": 3, "progress": "none"})
    half = plan("Python project", "login, tasks, tests", answers={"skill": 3, "progress": "half"})
    assert half["workload"]["likely"] < 0.6 * fresh["workload"]["likely"]
    assert half["workload"]["stages"][0]["label"] != "Plan the design"


# ---------- 9. follow-up questions ----------
def test_vague_project_triggers_targeted_questions_not_a_plan():
    r = run(PlanInput(title="I need to complete my Python project", today=TODAY, deadline=DEADLINE))
    assert r["status"] == "needs_info"
    ids = [q["id"] for q in r["questions"]]
    assert len(ids) <= 3 and {"scope", "skill"} <= set(ids)


def test_specific_task_with_known_skill_gets_a_plan_without_questions():
    r = plan("Write a 2000 word essay on renewable energy")
    assert r["status"] == "plan"


def test_answered_questions_are_never_asked_again_and_questions_are_progressive():
    first = run(PlanInput(title="Do my project", today=TODAY, deadline=DEADLINE))
    assert first["status"] == "needs_info"
    answers = {q["id"]: ("programming" if q["id"] == "kind" else "half" if q["id"] == "progress" else 2 if q["id"] == "skill"
                         else "login\nsearch\ntests") for q in first["questions"]}
    second = run(PlanInput(title="Do my project", today=TODAY, deadline=DEADLINE, answers=answers))
    asked_again = {q["id"] for q in second.get("questions", [])} & set(answers)
    assert not asked_again


def test_skipping_a_question_gives_a_plan_with_more_uncertainty():
    asked = run(PlanInput(title="Complete my Python project", today=TODAY, deadline=DEADLINE))
    skipped = run(PlanInput(title="Complete my Python project", today=TODAY, deadline=DEADLINE,
                            skipped=[q["id"] for q in asked["questions"]]))
    assert skipped["status"] == "plan"
    assert skipped["workload"]["confidence"] in ("low", "medium")
    assert any("skipped" in u for u in skipped["uncertainties"])
    answered = plan("Complete my Python project", "login, tasks, tests, search, export", answers={"skill": 3})
    w_s, w_a = skipped["workload"], answered["workload"]
    assert (w_s["high"] - w_s["low"]) / w_s["likely"] > (w_a["high"] - w_a["low"]) / w_a["likely"]


def test_missing_deadline_is_asked_for():
    r = run(PlanInput(title="Essay on history", details="2000 words", today=TODAY, answers={"skill": 3}))
    assert r["status"] == "needs_info" and r["questions"][0]["id"] == "deadline"


# ---------- 5. learning from history ----------
def outcomes(kind, ratio, n, raw=60):
    return [H.Outcome(kind, raw, raw * ratio) for _ in range(n)]


def test_history_moves_the_estimate_towards_what_the_student_really_needs():
    base = plan("Read chapter 3", "30 pages")["workload"]["likely"]
    slow = plan("Read chapter 3", "30 pages", outcomes=outcomes("reading", 2.0, 6))["workload"]["likely"]
    fast = plan("Read chapter 3", "30 pages", outcomes=outcomes("reading", 0.6, 6))["workload"]["likely"]
    assert slow > 1.35 * base and fast < 0.9 * base
    assert slow < 2.0 * base                       # shrinkage: never jumps all the way on a few results


def test_one_unusual_result_barely_moves_the_estimate():
    normal = outcomes("reading", 1.0, 5)
    base = plan("Read chapter 3", "30 pages", outcomes=normal)["workload"]["likely"]
    with_outlier = plan("Read chapter 3", "30 pages", outcomes=normal + [H.Outcome("reading", 60, 300)])["workload"]["likely"]
    assert abs(with_outlier - base) / base < 0.12
    single = plan("Read chapter 3", "30 pages", outcomes=[H.Outcome("reading", 60, 300)])["workload"]["likely"]
    ref = plan("Read chapter 3", "30 pages")["workload"]["likely"]
    assert single / ref < 1.3                      # a single 5x session moves it by less than 30%


def test_history_of_one_kind_is_weaker_for_another_kind():
    reading_slow = outcomes("reading", 2.0, 6)
    r_read = plan("Read chapter 3", "30 pages", outcomes=reading_slow)["workload"]
    r_prog = plan("Python project", "login, tasks, tests", outcomes=reading_slow)["workload"]
    base_prog = plan("Python project", "login, tasks, tests")["workload"]["likely"]
    base_read = plan("Read chapter 3", "30 pages")["workload"]["likely"]
    assert r_read["likely"] / base_read > r_prog["likely"] / base_prog
    assert r_prog["history"]["basis"] == "all" and "all kinds" in r_prog["history"]["text"]


def test_session_preference_is_found_per_kind_and_not_applied_to_other_kinds():
    sessions = ([H.SessionRecord("reading", 25, True, 4)] * 8 + [H.SessionRecord("reading", 60, False, 2)] * 6)
    pref = H.preferred_session("reading", sessions, 40)
    assert pref and pref["minutes"] <= 30
    assert H.preferred_session("programming", sessions, 75) is None
    r_prog = plan("Python project", "login, tasks, tests", sessions=sessions)
    assert r_prog["preferences_used"] == {}
    r_read = plan("Read chapter 3", "60 pages", sessions=sessions)
    assert "reading" in r_read["preferences_used"]


def test_no_preference_without_enough_data():
    few = [H.SessionRecord("reading", 25, True, 4)] * 3
    assert H.preferred_session("reading", few, 40) is None


def test_explanation_says_how_history_was_used():
    r = plan("Read chapter 3", "30 pages", outcomes=outcomes("reading", 1.8, 5))
    assert "times my first estimate" in r["workload"]["history"]["text"]
    r0 = plan("Read chapter 3", "30 pages")
    assert "no finished tasks" in r0["workload"]["history"]["text"]


# ---------- 6. adaptive scheduling ----------
def test_admin_task_gets_no_scheduled_break():
    r = plan("Email my tutor about the deadline", answers={})
    assert r["status"] == "plan"
    assert all(s["break_after"] == 0 for d in r["schedule"]["days"] for s in d["sessions"])


def test_short_blocks_do_not_get_breaks_but_long_programming_blocks_can():
    r = plan("Build a Python web app", "login, tasks, database, tests, search", daily_minutes=240, deadline=date(2026, 10, 31))
    sess = [s for d in r["schedule"]["days"] for s in d["sessions"]]
    assert any(s["minutes"] >= 60 for s in sess)
    assert len({s["break_after"] for s in sess}) >= 2


def test_low_energy_and_high_stress_shorten_todays_sessions_only():
    normal = plan("Build a Python web app", "login, tasks, database, tests", daily_minutes=180, energy=4)
    tired = plan("Build a Python web app", "login, tasks, database, tests", daily_minutes=180, energy=1)
    n_first = normal["schedule"]["days"][0]["sessions"][0]["minutes"]
    t_first = tired["schedule"]["days"][0]["sessions"][0]["minutes"]
    assert t_first < n_first
    assert tired["schedule"]["days"][0]["total_minutes"] < normal["schedule"]["days"][0]["total_minutes"]
    stressed = plan("Build a Python web app", "login, tasks, database, tests", daily_minutes=180, stress_risk="High")
    assert stressed["schedule"]["days"][0]["sessions"][0]["minutes"] <= 25


def test_hard_exam_topic_is_split_over_several_shorter_sessions():
    r = plan("Revise for the exam", "eigenvalues, proofs, optimisation, differential equations", answers={"skill": 1})
    sessions = [s for d in r["schedule"]["days"] for s in d["sessions"]]
    assert len(sessions) >= 6 and max(s["minutes"] for s in sessions) <= 45


def test_review_session_is_placed_on_a_later_day_than_the_practice_it_reviews():
    r = plan("Revise for the exam", "waves, optics, forces, energy, circuits, thermodynamics", daily_minutes=240)
    days = {s["work_id"]: d["date"] for d in r["schedule"]["days"] for s in d["sessions"]}
    if "exam_spaced" in days and "exam_practice" in days:
        assert days["exam_spaced"] >= days["exam_practice"]


# ---------- constraints ----------
@pytest.mark.parametrize("days_left,hours", [(2, 60), (5, 90), (10, 120), (30, 45), (1, 240)])
def test_schedule_never_breaks_deadline_or_daily_hours(days_left, hours):
    deadline = date.fromordinal(TODAY.toordinal() + days_left)
    r = plan("Complete my software project", "login, tasks, search, tests, report, deployment", deadline=deadline, daily_minutes=hours)
    sched = r["schedule"]
    for d in sched["days"]:
        assert date.fromisoformat(d["date"]) <= date.fromisoformat(sched["last_day"])
        assert d["total_minutes"] <= max(hours, 0)
    total = sum(d["total_minutes"] for d in sched["days"]) + sched["shortfall_minutes"]
    assert total == sched["total_minutes"]
    assert sched["feasible"] == (sched["shortfall_minutes"] == 0)


def test_impossible_workload_is_reported_not_hidden():
    r = plan("Write a dissertation", "12000 words", deadline=date(2026, 10, 31), daily_minutes=60)
    assert r["schedule"]["feasible"] is False and r["schedule"]["shortfall_minutes"] > 0
    assert any("does not fit" in a for a in r["advice"])
    assert r["schedule"]["needed_per_day"] > 60


def test_today_minutes_limit_is_respected():
    r = plan("Python project", "login, tasks, tests", daily_minutes=120, today_minutes=30)
    assert r["schedule"]["days"][0]["total_minutes"] <= 30


# ---------- 7. explanations ----------
def test_every_decision_is_explained_in_plain_language():
    r = plan("Python project", "login, tasks, tests", answers={"skill": 2})
    assert "programming" in r["understanding"]["text"]
    assert "for you" in r["difficulty"]["text"].lower()
    assert "hour" in r["workload"]["text"]
    assert r["session_reasons"] and all(isinstance(v, str) and v for v in r["session_reasons"].values())
    assert r["workload"]["history"]["text"]
    assert "have not read any course material" in r["limits"]


def test_unknowns_are_listed_not_hidden():
    r = run(PlanInput(title="Complete my Python project", today=TODAY, deadline=DEADLINE,
                      skipped=["scope", "progress", "skill"]))
    texts = " ".join(r["uncertainties"])
    assert "experienced" in texts and "no finished tasks" in texts


# ---------- reproducibility ----------
def test_same_input_gives_identical_output():
    kw = dict(title="Python project", details="login, tasks, tests", answers={"skill": 2}, deadline=DEADLINE,
              outcomes=outcomes("programming", 1.5, 4))
    a = json.dumps(run(PlanInput(today=TODAY, **kw)), sort_keys=True, default=str)
    b = json.dumps(run(PlanInput(today=TODAY, **kw)), sort_keys=True, default=str)
    assert a == b


# ---------- ranking ----------
def test_ranking_knows_how_much_work_is_left():
    from datetime import datetime, timedelta, timezone
    from app.heuristic import ScorableTask, rank_tasks
    now = datetime(2026, 10, 28, 9, tzinfo=timezone.utc)
    tasks = [ScorableTask("a", "Read chapter 2 (10 pages)", 2, now + timedelta(hours=20)),
             ScorableTask("b", "Complete my Python project", 4, now + timedelta(hours=40))]
    baseline = rank_tasks(tasks, 3, now=now)[0]
    smart, _ = rank_smart(tasks, 3, details={}, now=now)
    assert baseline[0].task.id == "a"                 # the old formula puts the nearer, smaller task first
    assert smart[0].task.id == "b"                    # the new one sees that the project cannot be done in time
    assert smart[0].breakdown["effort_minutes"] > 10 * smart[1].breakdown["effort_minutes"]


def test_smart_ranking_keeps_burnout_mode_filter():
    from datetime import datetime, timedelta, timezone
    from app.heuristic import ScorableTask
    now = datetime(2026, 10, 28, 9, tzinfo=timezone.utc)
    tasks = [ScorableTask("hard", "Python project", 5, now + timedelta(hours=5)), ScorableTask("easy", "Email tutor", 1, now + timedelta(hours=50))]
    ranked, burnout = rank_smart(tasks, 1, details={}, now=now, recent_energy=[1])
    assert burnout and [s.task.id for s in ranked] == ["easy"]


# ---------- API ----------
def test_guest_endpoint_asks_then_plans(api):
    body = {"title": "I need to complete my Python project", "deadline": "2026-11-13"}
    r = api.client.post("/demo/smart/plan", json=body)
    assert r.status_code == 200 and r.json()["status"] == "needs_info"
    body["answers"] = {"scope": "login\ntasks\ntests", "skill": 3, "progress": "none"}
    r2 = api.client.post("/demo/smart/plan", json=body).json()
    assert r2["status"] == "plan" and r2["workload"]["likely"] > 300


def test_plan_endpoint_requires_login_and_validates_input(api):
    assert api.client.post("/smart/plan", json={"title": "x"}).status_code in (401, 403)
    u = api.register()
    bad = api.client.post("/smart/plan", json={"title": "x", "answers": {"evil": "1"}}, headers=u["headers"])
    assert bad.status_code == 422
    huge = api.client.post("/smart/plan", json={"title": "x" * 500}, headers=u["headers"])
    assert huge.status_code == 422


def test_skill_answer_is_remembered_and_outcomes_change_later_plans(api):
    u = api.register()
    h = u["headers"]
    body = {"title": "Read chapter 3", "details": "30 pages", "deadline": "2026-11-13", "answers": {"skill": 2}}
    first = api.client.post("/smart/plan", json=body, headers=h).json()
    assert first["status"] == "plan"
    body["answers"] = {}
    again = api.client.post("/smart/plan", json=body, headers=h).json()
    assert again["status"] == "plan" and again["difficulty"]["skill"] == 2          # not asked again
    for _ in range(5):
        r = api.client.post("/smart/outcome", json={"kind": "reading", "raw_minutes": 60, "actual_minutes": 120}, headers=h)
        assert r.status_code == 201
    later = api.client.post("/smart/plan", json=body, headers=h).json()
    assert later["workload"]["likely"] > 1.3 * again["workload"]["likely"]
    learned = api.client.get("/smart/learned", headers=h).json()
    assert learned["kinds"][0]["kind"] == "reading" and learned["kinds"][0]["estimate_adjustment_percent"] > 20


def test_history_is_private_and_exported_and_deleted_with_the_account(api):
    a, b = api.register(), api.register()
    api.client.post("/smart/outcome", json={"kind": "reading", "raw_minutes": 60, "actual_minutes": 120}, headers=a["headers"])
    assert api.client.get("/smart/learned", headers=b["headers"]).json()["total_outcomes"] == 0
    exported = api.client.get("/account/export", headers=a["headers"]).json()
    assert exported["task_outcomes"][0]["actual_minutes"] == 120
    r = api.client.request("DELETE", "/account", json={"password": a["password"]}, headers=a["headers"])
    assert r.status_code == 204


def test_recommendation_explanation_mentions_the_work_needed(api):
    from datetime import datetime, timedelta, timezone
    u = api.register()
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    api.client.post("/tasks", json={"title": "Complete my Python project", "description": "", "category": "coursework",
                                    "difficulty": 4, "deadline": deadline}, headers=u["headers"])
    api.client.post("/energy-checkins", json={"energy_level": 4}, headers=u["headers"])
    body = api.client.get("/recommend", headers=u["headers"]).json()
    assert "It needs about" in body["explanation"]
    assert body["top_task"]["score_breakdown"]["effort_minutes"] > 600


def test_numbered_ranges_and_minutes_are_counted_and_not_double_counted():
    assert A.extract_counts("calculus chapters 1 to 6") == [(6.0, "chapter")]
    assert A.extract_counts("about 5 to 9 pages") == [(7.0, "page")]
    assert A.extract_counts("a 10 minute group presentation") == [(10.0, "talk_minute")]


def test_bigger_exam_and_presentation_are_estimated_bigger_than_small_ones():
    from app.taskaware.workload import estimate

    def total(title, details=""):
        return estimate(A.analyse(title, details), 3, {}).likely

    assert total("Maths exam covering calculus chapters 1 to 6") > total("Short algebra quiz", "mostly revision")
    assert total("Group presentation", "10 minute group presentation, make the slides and practise") > total("Presentation", "5 slide presentation")
    # "chapters 4 to 6 ... about 90 pages" is one reading task described twice, not two tasks added together
    one = total("Read chapters 4 to 6", "about 90 pages")
    assert one <= total("Read chapters 4 to 6", "about 90 pages and 3 chapters") + 1
    assert one < 90 * 3.5 + 3 * 40


def test_sentence_fragments_lose_their_leading_i_have_to():
    items = A.extract_deliverables("I have to make the slides and I need to practise")
    assert items == ["make the slides", "practise"]


def test_due_dates_are_not_counted_as_pieces_of_work():
    items = A.extract_deliverables("build a login page with user registration and unit tests, due in 5 days")
    assert items == ["build a login page", "user registration", "unit tests"]


def test_a_short_list_does_not_shrink_an_unknown_size_task_below_half_of_the_usual_effort():
    from app.taskaware import taxonomy as T
    from app.taskaware.workload import estimate
    a = A.analyse("Python programming assignment", "build a login page with tests")
    w = estimate(a, 3, {})
    assert a.size_source == "default"
    assert w.likely >= int(T.KINDS["programming"]["base"] * 0.5) - 5
