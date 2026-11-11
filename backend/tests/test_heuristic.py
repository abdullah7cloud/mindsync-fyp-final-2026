"""
Unit tests for the local recommendation heuristic. These test pure
functions only (no DB, no network, no LLM) — they should run in well
under a second and are what would be cited in Chapter 5/6 as evidence the
heuristic behaves as designed.
"""
from datetime import datetime, timedelta, timezone

from app.heuristic import (
    BURNOUT_MAX_DIFFICULTY,
    ScorableTask,
    compute_deadline_score,
    compute_energy_match_score,
    is_burnout_mode,
    rank_tasks,
    score_task,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _task(id_, title, difficulty, hours_until_due):
    return ScorableTask(
        id=id_,
        title=title,
        difficulty=difficulty,
        deadline=NOW + timedelta(hours=hours_until_due),
    )


# ---------- compute_deadline_score ----------

def test_deadline_score_overdue_task_is_maximally_urgent():
    assert compute_deadline_score(NOW - timedelta(hours=5), NOW) == 1.0


def test_deadline_score_within_urgent_horizon_is_max():
    assert compute_deadline_score(NOW + timedelta(hours=23), NOW) == 1.0


def test_deadline_score_decays_as_deadline_moves_further_away():
    soon = compute_deadline_score(NOW + timedelta(hours=48), NOW)
    later = compute_deadline_score(NOW + timedelta(hours=24 * 30), NOW)
    assert 0.0 < later < soon < 1.0


# ---------- compute_energy_match_score ----------

def test_energy_match_perfect_when_equal():
    assert compute_energy_match_score(task_difficulty=3, energy_level=3) == 1.0


def test_energy_match_decreases_with_mismatch():
    close = compute_energy_match_score(task_difficulty=3, energy_level=2)
    far = compute_energy_match_score(task_difficulty=5, energy_level=1)
    assert 0.0 <= far < close < 1.0


def test_energy_match_never_negative_at_max_mismatch():
    assert compute_energy_match_score(task_difficulty=5, energy_level=1) == 0.0


# ---------- score_task ----------

def test_score_task_breakdown_contains_both_components():
    t = _task("a", "Essay", difficulty=3, hours_until_due=12)
    scored = score_task(t, energy_level=3, now=NOW)
    assert "deadline_score" in scored.breakdown
    assert "energy_match_score" in scored.breakdown
    assert 0.0 <= scored.score <= 1.0


# ---------- is_burnout_mode ----------

def test_burnout_mode_false_with_no_history():
    assert is_burnout_mode([]) is False


def test_burnout_mode_true_after_single_low_checkin():
    assert is_burnout_mode([5, 5, 1]) is True


def test_burnout_mode_true_when_recent_window_all_low():
    assert is_burnout_mode([5, 5, 1, 2, 1]) is True


def test_burnout_mode_false_when_one_recent_reading_is_high():
    assert is_burnout_mode([1, 1, 4]) is False


# ---------- rank_tasks ----------

def test_rank_tasks_orders_most_urgent_matched_task_first():
    urgent = _task("urgent", "Due soon", difficulty=3, hours_until_due=2)
    distant = _task("distant", "Due later", difficulty=3, hours_until_due=24 * 60)
    ranked, burnout = rank_tasks([distant, urgent], energy_level=3, now=NOW)
    assert burnout is False
    assert ranked[0].task.id == "urgent"


def test_rank_tasks_excludes_hard_tasks_in_burnout_mode():
    easy = _task("easy", "Light task", difficulty=1, hours_until_due=5)
    hard = _task("hard", "Heavy task", difficulty=5, hours_until_due=5)
    ranked, burnout = rank_tasks(
        [easy, hard], energy_level=1, recent_energy_levels=[1, 1, 1], now=NOW
    )
    assert burnout is True
    assert all(t.task.difficulty <= BURNOUT_MAX_DIFFICULTY for t in ranked)
    assert [t.task.id for t in ranked] == ["easy"]


def test_rank_tasks_empty_list_returns_empty_ranking():
    ranked, burnout = rank_tasks([], energy_level=3, now=NOW)
    assert ranked == []
    assert burnout is False


def test_naive_deadline_is_treated_as_utc_and_does_not_crash():
    from datetime import datetime, timedelta, timezone
    from app.heuristic import ScorableTask, rank_tasks
    naive = (datetime.now(timezone.utc) + timedelta(hours=5)).replace(tzinfo=None)
    ranked, _ = rank_tasks([ScorableTask(id="a", title="t", difficulty=3, deadline=naive)], energy_level=3)
    assert ranked[0].task.deadline.tzinfo is not None
