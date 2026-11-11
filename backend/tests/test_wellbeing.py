"""
Wellbeing (stress-risk) model: training pipeline, JSON export, strict input validation,
explanations, API routes, database storage and the link to Burnout Mode.

The tests train on SYNTHETIC stand-in data (tests/standin.py) so they run anywhere without the
real survey file. They test the machinery, not real-world accuracy; real accuracy numbers come
from running the training script on the real dataset (see docs/WELLBEING_MODEL.md).
"""
import asyncio
import json
import math
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from app import wellbeing as wb_routes
from app.ml import wellbeing_model as wm
from tests.standin import make_standin_csv


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Run the real training script on stand-in data once; return (model, metrics dict)."""
    from ml_training import wellbeing_train

    d = tmp_path_factory.mktemp("wb")
    make_standin_csv(d / "data.csv", n=1500)
    argv = sys.argv
    sys.argv = ["x", "--csv", str(d / "data.csv"), "--weights-out", str(d / "w.json"),
                "--metrics-out", str(d / "m.json"), "--questions", str(d / "none.json"), "--standin"]
    try:
        wellbeing_train.main()
    finally:
        sys.argv = argv
    return wm.load_model(d / "w.json"), json.loads((d / "m.json").read_text())


GOOD = {"Study_Hours": 4.0, "Class_Attendance": 95, "Exam_Frequency": 1, "Assignment_Load": "Low", "Sleep_Hours": 8.5,
        "Social_Media_Use": 1.0, "Screen_Time": 2.0, "Physical_Exercise": 5, "Peer_Pressure": "Low",
        "Family_Support": "High", "Anxiety_Level": 2}
BAD = {**GOOD, "Sleep_Hours": 4.0, "Assignment_Load": "High", "Peer_Pressure": "High", "Family_Support": "Low",
       "Anxiety_Level": 9, "Exam_Frequency": 5, "Physical_Exercise": 0}


# ---------- calibration, uncertainty and data-structure checks ----------
def test_metrics_include_calibration_confidence_intervals_and_score_structure(trained):
    model, metrics = trained
    c = metrics["calibration_test_set"]
    assert 0.0 <= c["expected_calibration_error"] <= 1.0 and c["reliability_table"]
    assert sum(b["n"] for b in c["reliability_table"]) == metrics["split_rows"]["test"]
    lo, hi = metrics["bootstrap_95_ci_test_set"]["accuracy_95ci"]
    acc = metrics["shipped_model_test_details"]["accuracy"]
    assert lo <= acc <= hi
    assert metrics["score_structure"]["classes_are_score_cutoffs"] is True        # stand-in label is a score cut-off
    assert "probability_meaning" in model.card and "not the chance that you will burn out" in model.card["probability_meaning"]
    assert "calibration" in model.metrics and "bootstrap_95_ci" in model.metrics


def test_calibration_function_perfect_and_overconfident_cases():
    import numpy as np
    from ml_training.wellbeing_train import calibration
    y = np.array([0, 1, 2, 0, 1, 2])
    perfect = calibration(np.eye(3)[y], y, 3)
    assert perfect["expected_calibration_error"] == 0.0 and perfect["brier_score_multiclass"] == 0.0
    wrong = calibration(np.eye(3)[(y + 1) % 3], y, 3)               # 100 % sure and always wrong
    assert wrong["expected_calibration_error"] == 1.0


def test_questionnaire_wording_check_flags_mismatches(tmp_path):
    from ml_training.wellbeing_train import check_wording
    meta = [{"name": "Sleep_Hours", "type": "number"},
            {"name": "Peer_Pressure", "type": "choice", "options": [{"value": "Low"}, {"value": "High"}]}]
    f = tmp_path / "q.json"
    f.write_text(json.dumps({"Sleep_Hours": {"label": "Sleep"}, "Ghost": {"label": "x"}, "Peer_Pressure": {"options": {"Low": "Low"}}}))
    notes = " | ".join(check_wording(meta, f))
    assert "Ghost" in notes and "options without a label: ['High']" in notes
    assert check_wording(meta, tmp_path / "missing.json")[0].endswith("plain column names.")


# ---------- training pipeline ----------
def test_training_writes_complete_weights_and_metrics(trained):
    model, metrics = trained
    assert model is not None and model.labels == ["Low", "Medium", "High"]
    assert "SYNTHETIC STAND-IN" in model.trained_on                 # stand-in output is always labelled
    assert len(model.columns) == len(model.mean) == len(model.coef[0])
    split = metrics["split_rows"]
    assert split["train"] + split["validation"] + split["test"] == metrics["data_checks"]["rows"]
    assert abs(split["train"] / metrics["data_checks"]["rows"] - 0.6) < 0.02          # 60/20/20


def test_training_excludes_label_leaking_and_demographic_columns(trained):
    _, metrics = trained
    used = set(metrics["features_used"])
    assert "Stress_Score" not in used and not used & {"Age", "Gender", "University_Type", "Tuition", "Family_Income_Level"}
    assert metrics["honesty_checks"]["with_stress_score_column_accuracy"] > 0.95      # proves why it is excluded


def test_model_beats_majority_baseline_on_held_out_test(trained):
    model, metrics = trained
    test = metrics["test_set_results_all_models"]
    assert test["logistic_regression_shipped"]["accuracy"] > test["majority_class_baseline"]["accuracy"] + 0.15
    assert model.metrics["cross_validation_macro_f1_mean"] > 0.5


# ---------- inference ----------
def test_prediction_shape_and_probabilities(trained):
    model, _ = trained
    r = model.predict(GOOD)
    assert r["label"] in model.labels
    assert math.isclose(sum(r["probabilities"].values()), 1.0, abs_tol=1e-3)
    assert r["confidence"] == max(r["probabilities"].values())


def test_unhealthy_habits_score_higher_risk_than_healthy_habits(trained):
    model, _ = trained
    assert model.predict(BAD)["probabilities"]["High"] > model.predict(GOOD)["probabilities"]["High"] + 0.4
    assert model.predict(BAD)["label"] == "High" and model.predict(GOOD)["label"] == "Low"


def test_explanations_point_at_the_right_answers(trained):
    model, _ = trained
    bad = model.predict(BAD)
    assert bad["factors_up"] and bad["factors_up"][0]["effect"] > 0
    names = {f["feature"] for f in bad["factors_up"]}
    assert names & {"Anxiety_Level", "Sleep_Hours", "Assignment_Load"}
    assert all(f["effect"] < 0 for f in model.predict(GOOD)["factors_down"])


@pytest.mark.parametrize("mutate, fragment", [
    (lambda a: a.pop("Sleep_Hours"), "Please answer"),
    (lambda a: a.update(Surprise=1), "Unknown question"),
    (lambda a: a.update(Sleep_Hours=99), "between"),
    (lambda a: a.update(Sleep_Hours=True), "must be a number"),
    (lambda a: a.update(Sleep_Hours=float("nan")), "must be a number"),
    (lambda a: a.update(Sleep_Hours="8"), "must be a number"),
    (lambda a: a.update(Assignment_Load="Extreme"), "must be one of"),
    (lambda a: a.update(Assignment_Load=3), "must be one of"),
])
def test_invalid_answers_are_rejected_with_readable_messages(trained, mutate, fragment):
    model, _ = trained
    answers = dict(GOOD)
    mutate(answers)
    with pytest.raises(wm.AnswerError, match=fragment):
        model.predict(answers)


def test_non_dict_answers_rejected(trained):
    with pytest.raises(wm.AnswerError):
        trained[0].predict(["not", "a", "dict"])


def test_load_model_rejects_missing_corrupt_and_inconsistent_files(tmp_path, trained):
    assert wm.load_model(tmp_path / "missing.json") is None
    (tmp_path / "bad.json").write_text("{nope")
    assert wm.load_model(tmp_path / "bad.json") is None
    raw = json.loads(json.dumps({k: getattr(trained[0], k) for k in ("version", "kind", "trained_on", "labels", "features", "columns", "coef", "intercept")}
                                | {"scaler_mean": trained[0].mean, "scaler_scale": trained[0].scale}))
    raw["scaler_mean"] = raw["scaler_mean"][:-1]                     # wrong length
    (tmp_path / "short.json").write_text(json.dumps(raw))
    assert wm.load_model(tmp_path / "short.json") is None


# ---------- API: guest + account routes ----------
@pytest.fixture()
def model_on(monkeypatch, trained):
    monkeypatch.setattr(wm, "MODEL", trained[0])
    return trained[0]


def test_routes_say_unavailable_when_model_is_not_trained(api, monkeypatch):
    monkeypatch.setattr(wm, "MODEL", None)
    assert api.client.get("/wellbeing/model").json() == {"available": False}
    assert api.client.post("/demo/wellbeing/assess", json={"answers": GOOD}).status_code == 503


def test_model_info_is_public_and_describes_the_questionnaire(api, model_on):
    info = api.client.get("/wellbeing/model").json()
    assert info["available"] and {q["name"] for q in info["questions"]} == set(GOOD)
    assert info["card"]["limitations"] and info["metrics"]["held_out_test_set"]["accuracy"] > 0


def test_guest_assess_works_stores_nothing_and_validates(api, model_on):
    ok = api.client.post("/demo/wellbeing/assess", json={"answers": BAD})
    assert ok.status_code == 200 and ok.json()["label"] == "High" and "diagnosis" in ok.json()["disclaimer"]
    bad = api.client.post("/demo/wellbeing/assess", json={"answers": {**GOOD, "Sleep_Hours": 99}})
    assert bad.status_code == 422 and "between" in bad.json()["detail"]


def test_account_assess_requires_login_and_saves_history(api, model_on):
    assert api.client.post("/wellbeing/assess", json={"answers": GOOD}).status_code in (401, 403)
    u = api.register()
    r = api.client.post("/wellbeing/assess", json={"answers": BAD}, headers=u["headers"])
    assert r.status_code == 200 and r.json()["label"] == "High" and r.json()["created_at"]
    api.client.post("/wellbeing/assess", json={"answers": GOOD}, headers=u["headers"])
    hist = api.client.get("/wellbeing/history", headers=u["headers"]).json()
    assert [h["label"] for h in hist] == ["Low", "High"]             # newest first
    other = api.register()
    assert api.client.get("/wellbeing/history", headers=other["headers"]).json() == []   # own data only


def test_high_result_switches_on_burnout_mode_in_recommend(api, model_on):
    u = api.register()
    soon = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    for title, diff in (("hard", 5), ("easy", 1)):
        api.client.post("/tasks", headers=u["headers"], json={"title": title, "difficulty": diff, "deadline": soon})
    api.client.post("/energy-checkins", json={"energy_level": 5}, headers=u["headers"])
    before = api.client.get("/recommend", headers=u["headers"]).json()
    assert before["burnout_mode"] is False and len(before["ranked_tasks"]) == 2
    api.client.post("/wellbeing/assess", json={"answers": BAD}, headers=u["headers"])
    after = api.client.get("/recommend", headers=u["headers"]).json()
    assert after["burnout_mode"] is True and after["burnout_reason"] == "high_stress_risk"
    assert [t["task"]["title"] for t in after["ranked_tasks"]] == ["easy"]


def test_low_result_does_not_change_the_ranking(api, model_on):
    u = api.register()
    soon = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    api.client.post("/tasks", headers=u["headers"], json={"title": "hard", "difficulty": 5, "deadline": soon})
    api.client.post("/energy-checkins", json={"energy_level": 5}, headers=u["headers"])
    api.client.post("/wellbeing/assess", json={"answers": GOOD}, headers=u["headers"])
    assert api.client.get("/recommend", headers=u["headers"]).json()["burnout_mode"] is False


# ---------- database: constraints, cascade and "fresh result" window ----------
def _run_db(coro_fn):
    pytest.importorskip("aiosqlite")
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool
    from app.database import Base

    async def go():
        from tests.dbutil import make_engine
        engine = await make_engine(foreign_keys=True)
        Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with Session() as db:
                return await coro_fn(db)
        finally:
            await engine.dispose()
    return asyncio.run(go())


def _user():
    from app.models import User
    return User(id=uuid.uuid4(), email=f"{uuid.uuid4().hex[:6]}@example.com", password_hash="x", display_name="D")


def test_database_rejects_invalid_label_and_difficulty():
    from sqlalchemy.exc import IntegrityError
    from app.models import Task, WellbeingCheck

    async def go(db):
        u = _user()
        uid = u.id                     # read now: after a rollback SQLAlchemy would reload it lazily
        db.add(u)
        await db.commit()
        db.add(WellbeingCheck(user_id=uid, answers={}, risk_label="Extreme", probabilities={}, model_version="v"))
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()
        db.add(Task(owner_id=uid, title="x", difficulty=9, deadline=datetime.now(timezone.utc)))
        with pytest.raises(IntegrityError):
            await db.commit()
        return True
    assert _run_db(go)


def test_deleting_a_user_deletes_their_wellbeing_checks():
    from sqlalchemy import func, select
    from app.models import WellbeingCheck

    async def go(db):
        u = _user()
        db.add(u)
        await db.commit()
        db.add(WellbeingCheck(user_id=u.id, answers={}, risk_label="Low", probabilities={}, model_version="v"))
        await db.commit()
        await db.delete(u)
        await db.commit()
        return await db.scalar(select(func.count()).select_from(WellbeingCheck))
    assert _run_db(go) == 0


def test_only_fresh_results_count():
    from app.models import WellbeingCheck

    async def go(db):
        u = _user()
        db.add(u)
        await db.commit()
        old = datetime.now(timezone.utc) - timedelta(days=wb_routes.RESULT_VALID_DAYS + 1)
        db.add(WellbeingCheck(user_id=u.id, answers={}, risk_label="High", probabilities={}, model_version="v", created_at=old))
        await db.commit()
        stale = await wb_routes.latest_recent_label(db, u.id)
        db.add(WellbeingCheck(user_id=u.id, answers={}, risk_label="Medium", probabilities={}, model_version="v"))
        await db.commit()
        return stale, await wb_routes.latest_recent_label(db, u.id)
    assert _run_db(go) == (None, "Medium")
