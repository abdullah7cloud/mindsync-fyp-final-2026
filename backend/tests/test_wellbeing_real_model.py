"""
Tests of the SHIPPED wellbeing model (app/ml/wellbeing_weights.json), trained on the real dataset.

They are skipped when the weights file is missing or is a synthetic stand-in. What they check:
  * the questionnaire matches the model's features (the app builds the form from the same file);
  * the model agrees with the dataset's own scoring rule (recovered exactly by the trainer: see docs/WELLBEING_MODEL.md);
  * extreme answers behave sensibly, and the card does not over-claim.
The scoring rule is written out here ONLY as an independent oracle for testing; the app never uses it.
"""
import random

import pytest

from app.ml import wellbeing_model as wm

M = wm.MODEL
pytestmark = pytest.mark.skipif(M is None or "STAND-IN" in (M.trained_on or "").upper(),
                                reason="real wellbeing model not installed")

EXPECTED = ["Exam_Frequency", "Assignment_Load", "Sleep_Hours", "Social_Media_Use", "Screen_Time",
            "Physical_Exercise", "Family_Support", "Anxiety_Level"]


def rule_band(a: dict) -> str:
    """Dataset scoring rule recovered by ml_training/wellbeing_train.py (R^2 = 1.0): used only as a test oracle."""
    score = (a["Exam_Frequency"] + a["Assignment_Load"] - a["Sleep_Hours"] + a["Social_Media_Use"] + a["Screen_Time"]
             - (2 if a["Physical_Exercise"] == "Yes" else 0) - a["Family_Support"] + a["Anxiety_Level"])
    return "Low" if score <= 10 else "Medium" if score <= 20 else "High"


def random_answers(rng: random.Random) -> dict:
    out = {}
    for q in M.features:
        out[q["name"]] = rng.choice([o["value"] for o in q["options"]]) if q["type"] == "choice" \
            else rng.randint(int(q["min"]), int(q["max"]))
    return out


def test_questionnaire_matches_trained_features():
    assert [q["name"] for q in M.features] == EXPECTED
    assert len(M.features) == 8


def test_model_agrees_with_the_datasets_scoring_rule():
    rng = random.Random(1)
    rows = [random_answers(rng) for _ in range(600)]
    agree = sum(M.predict(r)["label"] == rule_band(r) for r in rows) / len(rows)
    assert agree >= 0.97, agree


def test_extreme_answers():
    worst = {"Exam_Frequency": 9, "Assignment_Load": 9, "Sleep_Hours": 4, "Social_Media_Use": 7, "Screen_Time": 11,
             "Physical_Exercise": "No", "Family_Support": 1, "Anxiety_Level": 9}
    best = {"Exam_Frequency": 1, "Assignment_Load": 1, "Sleep_Hours": 9, "Social_Media_Use": 0, "Screen_Time": 1,
            "Physical_Exercise": "Yes", "Family_Support": 9, "Anxiety_Level": 1}
    assert M.predict(worst)["label"] == "High"
    assert M.predict(best)["label"] == "Low"


def test_probabilities_sum_to_one_and_explanations_point_the_right_way():
    rng = random.Random(2)
    for _ in range(50):
        res = M.predict(random_answers(rng))
        assert abs(sum(res["probabilities"].values()) - 1) < 1e-3
    res = M.predict({"Exam_Frequency": 9, "Assignment_Load": 9, "Sleep_Hours": 4, "Social_Media_Use": 7, "Screen_Time": 11,
                     "Physical_Exercise": "No", "Family_Support": 1, "Anxiety_Level": 9})
    assert len(res["factors_up"]) >= 3 and all(f["effect"] > 0 for f in res["factors_up"])


def test_card_does_not_overclaim():
    card = M.card
    assert "not the chance that you will burn out" in card["probability_meaning"]
    assert card["not_for"]
    assert any("scoring rule" in l for l in card["limitations"])
