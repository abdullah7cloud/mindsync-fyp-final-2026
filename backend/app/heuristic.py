"""
The local recommendation heuristic — Objective 3 of the project contract:
"a fast local recommendation heuristic that matches task difficulty and
deadline priority with user energy levels".

Everything in this file is pure, synchronous, deterministic Python with no
network or database calls and no external AI involvement. That is a deliberate
design choice (see Chapter 1 Problem Statement / Chapter 2 Research Gap):
the ranking a student sees must be explainable and reproducible, and must
keep working even when every external API is unreachable (the contract's
"full offline fallback functionality" requirement). Being pure functions
also makes this module trivially unit-testable (see tests/test_heuristic.py)
and keeps it fast enough to comfortably fit inside the sub-3-second
end-to-end latency budget — this step alone is sub-millisecond even for a
large task list.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

# Relative importance of "how soon is it due" vs "how well does the
# difficulty suit my current energy". Deadline pressure is weighted higher
# because a missed deadline is the harder failure mode for a burnt-out
# student to recover from; energy match still meaningfully shifts ranking
# between tasks with similar urgency.
DEADLINE_WEIGHT = 0.6
ENERGY_MATCH_WEIGHT = 0.4

# A task due within this many hours is treated as maximally urgent.
URGENT_HORIZON_HOURS = 24.0

# Burnout Mode (Phase 4 of the contract schedule): triggered when the
# student's last BURNOUT_WINDOW energy check-ins are all at/below
# BURNOUT_ENERGY_THRESHOLD. While active, recommendations are restricted to
# low-difficulty tasks to avoid piling pressure on an already low-energy
# student.
#
# BURNOUT_WINDOW = 1: a single low energy check-in is enough to trigger it
# immediately. An earlier version required 3 low check-ins in a row (to
# avoid reacting to one noisy/off-day reading), but that made the feature
# invisible in a quick demo or a first-time use — a student had no way to
# discover it without checking in low three separate times. Immediate,
# one-click feedback is more usable and more demoable, at the cost of being
# slightly more sensitive to a single low reading; worth noting as a design
# trade-off in the critical analysis chapter.
BURNOUT_WINDOW = 1
BURNOUT_ENERGY_THRESHOLD = 2
BURNOUT_MAX_DIFFICULTY = 2


@dataclass(frozen=True)
class ScorableTask:
    """
    The minimal, framework-independent view of a task that the heuristic
    needs. Callers (app/recommend.py) build this from the SQLAlchemy Task
    ORM object so this module never has to import app.models or touch a
    database session.
    """
    id: str
    title: str
    difficulty: int  # 1..5
    deadline: datetime  # timezone-aware (UTC)

    def __post_init__(self):
        # A deadline without a time zone (some databases drop it) is read as UTC,
        # so subtracting it from an aware "now" can never crash the ranking.
        if self.deadline.tzinfo is None:
            object.__setattr__(self, "deadline", self.deadline.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class ScoredTask:
    task: ScorableTask
    score: float
    breakdown: dict = field(default_factory=dict)


def compute_deadline_score(deadline: datetime, now: datetime) -> float:
    """
    1.0 = overdue or due within URGENT_HORIZON_HOURS; decays smoothly
    towards 0.0 the further away the deadline is. Never negative.
    """
    hours_remaining = (deadline - now).total_seconds() / 3600.0
    if hours_remaining <= URGENT_HORIZON_HOURS:
        return 1.0
    # Smooth hyperbolic decay beyond the urgent horizon, so a task due
    # tomorrow clearly outranks one due next month without a hard cliff.
    excess_hours = hours_remaining - URGENT_HORIZON_HOURS
    return max(0.0, URGENT_HORIZON_HOURS / (URGENT_HORIZON_HOURS + excess_hours))


def compute_energy_match_score(task_difficulty: int, energy_level: int) -> float:
    """
    1.0 when the task's difficulty exactly matches the student's current
    energy level (a 5-energy student tackling a 5-difficulty task, or a
    2-energy student tackling a 2-difficulty task); decreases linearly as
    the mismatch grows in either direction. Clamped to [0, 1].
    """
    mismatch = abs(task_difficulty - energy_level)
    return max(0.0, 1.0 - (mismatch / 4.0))


def is_burnout_mode(recent_energy_levels: list[int]) -> bool:
    """
    True when there is enough recent history (>= BURNOUT_WINDOW check-ins)
    and every one of the most recent BURNOUT_WINDOW readings is at or below
    BURNOUT_ENERGY_THRESHOLD. `recent_energy_levels` must be ordered oldest
    -> newest.
    """
    if len(recent_energy_levels) < BURNOUT_WINDOW:
        return False
    window = recent_energy_levels[-BURNOUT_WINDOW:]
    return all(level <= BURNOUT_ENERGY_THRESHOLD for level in window)


# Optional learned scorer: (task, energy_level, now) -> probability 0..1 that
# the task is a good fit right now. Supplied by app/ml (trained model). Kept
# as a plain callable so this module stays pure and free of any ML imports.
MlScorer = Callable[[ScorableTask, int, datetime], float]


def score_task(
    task: ScorableTask,
    energy_level: int,
    now: datetime,
    ml_scorer: Optional[MlScorer] = None,
    ml_weight: float = 0.0,
) -> ScoredTask:
    deadline_score = compute_deadline_score(task.deadline, now)
    energy_score = compute_energy_match_score(task.difficulty, energy_level)
    heuristic_total = (DEADLINE_WEIGHT * deadline_score) + (ENERGY_MATCH_WEIGHT * energy_score)
    breakdown = {
        "deadline_score": round(deadline_score, 4),
        "energy_match_score": round(energy_score, 4),
        "deadline_weight": DEADLINE_WEIGHT,
        "energy_match_weight": ENERGY_MATCH_WEIGHT,
    }
    total = heuristic_total
    if ml_scorer is not None and ml_weight > 0.0:
        try:
            ml_score = float(ml_scorer(task, energy_level, now))
        except Exception:
            ml_score = None   # any model problem -> plain heuristic, never an error
        if ml_score is not None:
            total = (1.0 - ml_weight) * heuristic_total + ml_weight * ml_score
            breakdown["heuristic_score"] = round(heuristic_total, 4)
            breakdown["ml_score"] = round(ml_score, 4)
            breakdown["ml_weight"] = ml_weight
    return ScoredTask(task=task, score=round(total, 4), breakdown=breakdown)


def rank_tasks(
    tasks: list[ScorableTask],
    energy_level: int,
    recent_energy_levels: list[int] | None = None,
    now: datetime | None = None,
    ml_scorer: Optional[MlScorer] = None,
    ml_weight: float = 0.0,
    extra_burnout: bool = False,
) -> tuple[list[ScoredTask], bool]:
    """
    Returns (ranked_tasks, burnout_mode) where ranked_tasks is sorted
    highest-score-first. When burnout mode is active, tasks with difficulty
    above BURNOUT_MAX_DIFFICULTY are excluded from the ranking entirely
    (not merely scored lower) — the student should not be shown a demanding
    task as a "top pick" while in this state.

    `extra_burnout` lets another signal switch Burnout Mode on too: the
    caller sets it when the trained wellbeing model recently predicted a
    High stress risk (see app/recommend.py). The heuristic itself stays a
    pure function - it does not know where the flag came from.
    """
    now = now or datetime.now(timezone.utc)
    burnout = is_burnout_mode(recent_energy_levels or []) or extra_burnout

    candidates = (
        [t for t in tasks if t.difficulty <= BURNOUT_MAX_DIFFICULTY] if burnout else list(tasks)
    )

    scored = [score_task(t, energy_level, now, ml_scorer, ml_weight) for t in candidates]
    scored.sort(key=lambda st: st.score, reverse=True)
    return scored, burnout
