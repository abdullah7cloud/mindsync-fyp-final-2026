"""Tests for the trained task-fit model and its integration with the heuristic."""
from datetime import datetime, timedelta, timezone

from app.heuristic import ScorableTask, rank_tasks
from app.ml.features import FEATURE_NAMES, build_features
from app.ml.predictor import MODEL, load_model, task_fit_scorer

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def _task(tid, difficulty, hours):
    return ScorableTask(id=tid, title=tid, difficulty=difficulty, deadline=NOW + timedelta(hours=hours))


def test_shipped_weights_load_and_match_feature_list():
    assert MODEL is not None
    assert len(MODEL.mean) == len(FEATURE_NAMES)


def test_probability_is_between_0_and_1():
    for d in range(1, 6):
        for e in range(1, 6):
            p = MODEL.predict_proba(build_features(d, e, 30.0))
            assert 0.0 <= p <= 1.0


def test_model_learned_hard_task_is_worse_when_tired():
    hard_tired = MODEL.predict_proba(build_features(5, 1, 30.0))
    hard_energised = MODEL.predict_proba(build_features(5, 5, 30.0))
    assert hard_energised > hard_tired + 0.2


def test_missing_weights_file_returns_none(tmp_path):
    assert load_model(tmp_path / "does_not_exist.json") is None


def test_corrupt_weights_file_returns_none(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_model(bad) is None


def test_ranking_with_ml_still_sorted_and_reports_ml_score():
    tasks = [_task("a", 2, 20), _task("b", 5, 20), _task("c", 3, 200)]
    ranked, _ = rank_tasks(tasks, energy_level=2, now=NOW, ml_scorer=task_fit_scorer, ml_weight=0.3)
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)
    assert "ml_score" in ranked[0].breakdown


def test_failing_scorer_falls_back_to_plain_heuristic():
    def boom(*_args):
        raise RuntimeError("model exploded")

    tasks = [_task("a", 2, 20), _task("b", 5, 20)]
    plain, _ = rank_tasks(tasks, energy_level=2, now=NOW)
    safe, _ = rank_tasks(tasks, energy_level=2, now=NOW, ml_scorer=boom, ml_weight=0.5)
    assert [r.score for r in plain] == [r.score for r in safe]
    assert "ml_score" not in safe[0].breakdown


def test_burnout_mode_still_filters_hard_tasks_with_ml():
    tasks = [_task("easy", 1, 100), _task("hard", 5, 1)]
    ranked, burnout = rank_tasks(tasks, energy_level=1, recent_energy_levels=[1],
                                 now=NOW, ml_scorer=task_fit_scorer, ml_weight=0.3)
    assert burnout is True
    assert [r.task.id for r in ranked] == ["easy"]
