"""Study Planner: rule-based ratings, mode-based blocks, ordering rules, stress-risk adjustment, guest + login routes."""
import pytest
from fastapi.testclient import TestClient

from app import demo, planner
from app.main import app
from app.planner import PlanRequest, RatedTopic, TopicIn, build_plan, effective_energy, make_plan, mode_for, offline_rate
from app.ratelimit import LoginRateLimiter


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(demo, "demo_rank_limiter", LoginRateLimiter(120, 600))


client = TestClient(app)


def rt(title, d, minutes=None):
    return RatedTopic(title=title, difficulty=d, minutes=minutes or planner.DEFAULT_MINUTES[d], source="student")


# ---------- offline ratings ----------
def test_offline_rules_known_and_keywords():
    assert offline_rate("Python basics")[0] == 2
    assert offline_rate("HTML")[0] == 1
    assert offline_rate("Advanced machine learning")[0] == 5
    assert offline_rate("Introduction to calculus")[0] == 3
    assert offline_rate("Some unknown topic")[0] == 3
    d, mins, why = offline_rate("Power BI")
    assert 1 <= d <= 5 and mins == planner.DEFAULT_MINUTES[d] and why


def test_c_does_not_match_inside_other_words():
    assert offline_rate("Chocolate chemistry")[0] == 3     # not treated as the language "c"


# ---------- modes ----------
def test_mode_block_lengths():
    assert mode_for(1)[:3] == ("low", 15, 10) and mode_for(2)[:3] == ("low", 15, 10)
    assert mode_for(3)[:3] == ("normal", 20, 5)
    assert mode_for(4)[:3] == ("normal", 25, 5)
    assert mode_for(5)[:3] == ("high", 45, 10)


def test_low_energy_defers_hard_topics():
    r = build_plan("CS", [rt("easy", 1), rt("hard", 5), rt("mid", 3)], 1, None)
    studied = {i.topic for i in r["plan"] if i.kind == "study"}
    assert studied == {"easy"} and set(r["deferred"]) == {"hard", "mid"}
    assert all(i.minutes <= 15 for i in r["plan"] if i.kind == "study")


def test_low_energy_all_hard_gives_one_gentle_block():
    r = build_plan("CS", [rt("a", 5), rt("b", 4)], 1, None)
    study = [i for i in r["plan"] if i.kind == "study"]
    assert len(study) == 1 and study[0].topic == "b" and study[0].minutes <= 15


# ---------- ordering ----------
def test_first_block_easy_when_normal_hard_when_energy_high():
    topics = [rt("hard", 5, 20), rt("easy", 1, 20), rt("mid", 3, 20)]
    first_normal = next(i for i in build_plan("x", topics, 3, None)["plan"] if i.kind == "study")
    first_high = next(i for i in build_plan("x", topics, 5, None)["plan"] if i.kind == "study")
    assert first_normal.topic == "easy" and first_high.topic == "hard"


def test_no_two_hard_blocks_back_to_back_when_avoidable():
    topics = [rt("h1", 5, 60), rt("h2", 4, 60), rt("e1", 1, 60), rt("e2", 2, 60)]
    plan = [i for i in build_plan("x", topics, 5, None)["plan"] if i.kind == "study"]
    for a, b in zip(plan, plan[1:]):
        assert not (a.difficulty >= 4 and b.difficulty >= 4)


def test_long_break_after_every_fourth_block_and_no_trailing_break():
    topics = [rt("a", 2, 100), rt("b", 3, 100)]       # many 20-min blocks
    plan = build_plan("x", topics, 3, None)["plan"]
    kinds = [i.kind for i in plan]
    assert kinds[-1] == "review" and "long_break" in kinds
    study_seen = 0
    for i in plan:
        if i.kind == "study":
            study_seen += 1
        if i.kind == "long_break":
            assert study_seen % 4 == 0


def test_start_minutes_are_continuous_and_totals_add_up():
    r = build_plan("x", [rt("a", 2, 40), rt("b", 4, 40)], 3, None)
    clock = 0
    for i in r["plan"]:
        assert i.start_minute == clock
        clock += i.minutes
    assert r["total_minutes"] == clock
    assert r["study_minutes"] == sum(i.minutes for i in r["plan"] if i.kind in ("study", "review"))


def test_available_time_is_respected_and_rest_deferred():
    topics = [rt("a", 3, 90), rt("b", 3, 90), rt("c", 2, 90)]
    r = build_plan("x", topics, 3, 60)
    assert r["total_minutes"] <= 60 and r["deferred"]


def test_single_topic_has_no_review_and_parts_are_numbered():
    r = build_plan("x", [rt("only", 3, 60)], 3, None)
    assert all(i.kind != "review" for i in r["plan"])
    assert "part 1 of 3" in r["plan"][0].label


def test_block_count_is_capped():
    r = build_plan("x", [rt(f"t{i}", 5, 240) for i in range(15)], 5, None)
    assert len([i for i in r["plan"] if i.kind == "study"]) <= planner.MAX_TOTAL_BLOCKS


# ---------- ratings + wellbeing adjustment ----------
def test_student_rating_is_kept_and_rules_fill_the_rest():
    res = make_plan(PlanRequest(topics=[TopicIn(title="Calculus", difficulty=1), TopicIn(title="Python basics")]))
    by = {t.title: t for t in res.topics}
    assert by["Calculus"].source == "student" and by["Calculus"].difficulty == 1
    assert by["Python basics"].source == "offline_rules"
    assert res.rating_source == "mixed" and res.note


def test_high_stress_risk_forces_gentle_mode_and_medium_caps_at_normal():
    assert effective_energy(5, "High") == 2 and effective_energy(5, "Medium") == 3
    assert effective_energy(5, "Low") == 5 and effective_energy(4, None) == 4
    assert effective_energy(1, "Medium") == 1                      # never raised
    res = make_plan(PlanRequest(topics=[TopicIn(title="Python basics"), TopicIn(title="Machine learning")],
                                energy=5, stress_risk="High"))
    assert res.mode == "low" and "High stress level" in res.note


# ---------- input validation ----------
def test_request_validation_dedupes_and_limits():
    r = PlanRequest(topics=[TopicIn(title="  Python   basics "), TopicIn(title="python basics")])
    assert len(r.topics) == 1 and r.topics[0].title == "Python basics"
    with pytest.raises(ValueError):
        PlanRequest(topics=[TopicIn(title=f"t{i}") for i in range(16)])
    with pytest.raises(ValueError):
        TopicIn(title="x" * 81)
    with pytest.raises(ValueError):
        TopicIn(title="   ")


# ---------- routes ----------
def test_guest_route_needs_no_login_and_works_offline():
    r = client.post("/demo/planner/plan", json={"category": "Computer Science", "energy": 3,
                    "topics": [{"title": "Python basics"}, {"title": "Power BI"}, {"title": "SQL joins"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "normal" and body["block_minutes"] == 20 and body["rating_source"] == "offline_rules"
    assert "provider" not in body
    assert any(i["kind"] == "study" for i in body["plan"])


def test_guest_route_rejects_bad_input():
    assert client.post("/demo/planner/plan", json={"topics": []}).status_code == 422
    assert client.post("/demo/planner/plan", json={"topics": [{"title": "a"}], "energy": 9}).status_code == 422
    assert client.post("/demo/planner/plan", json={"topics": [{"title": "a", "difficulty": 7}]}).status_code == 422


def test_account_route_requires_login():
    assert client.post("/planner/plan", json={"topics": [{"title": "a"}]}).status_code == 401


def test_light_topics_are_finished_in_one_run():
    topics = [rt("easy", 2, 60), rt("hard", 5, 30), rt("mid", 3, 40)]
    study = [i.topic for i in build_plan("x", topics, 3, None)["plan"] if i.kind == "study"]
    for t in ("easy", "mid"):
        idx = [n for n, x in enumerate(study) if x == t]
        assert idx == list(range(idx[0], idx[0] + len(idx)))      # consecutive blocks
