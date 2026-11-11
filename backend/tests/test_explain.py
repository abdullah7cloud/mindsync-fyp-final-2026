"""The plain-English explanation: deterministic, honest, and covers every situation."""
from app.explain import explain_recommendation as ex

URGENT = {"deadline_score": 1.0, "energy_match_score": 1.0, "ml_score": 0.72}


def test_urgent_matching_task_mentions_both_reasons_and_model():
    t = ex("Essay", 3, URGENT, 3, False)
    assert "'Essay' is first because" in t and "very close" in t and "exactly matches" in t and "72%" in t


def test_without_model_score_no_percentage_is_claimed():
    assert "%" not in ex("Essay", 3, {"deadline_score": 0.2, "energy_match_score": 0.5}, 3, False)


def test_harder_and_easier_than_energy_are_described_correctly():
    hard = ex("A", 5, {"deadline_score": 1.0, "energy_match_score": 0.25}, 2, False)
    easy = ex("A", 1, {"deadline_score": 0.2, "energy_match_score": 0.25}, 4, False)
    assert "harder" in hard and "easier" in easy


def test_burnout_reasons_are_named():
    assert "latest energy check-in was low" in ex("A", 1, URGENT, 1, True, "low_energy")
    assert "wellbeing check estimated a high stress level" in ex("A", 1, URGENT, 5, True, "high_stress_risk")


def test_empty_states():
    assert "no pending tasks" in ex(None, None, {}, 3, False).lower()
    assert "Burnout Mode is on" in ex(None, None, {}, 1, True, "low_energy")


def test_same_input_gives_same_text():
    assert ex("A", 3, URGENT, 3, False) == ex("A", 3, URGENT, 3, False)
