"""
Ranking that knows how MUCH work each task needs.

The original heuristic (app/heuristic.py, kept unchanged as the evaluation baseline) ranks by how close the
deadline is and how well the task's difficulty matches the student's energy. It cannot tell a ten-minute reading
due tomorrow from a twenty-hour project due the day after. This ranking adds the missing piece, work pressure:

    pressure   = how much of the time available before the deadline the task will need
                 (estimated remaining minutes / minutes the student can study before the deadline)
    urgency    = 0.4 x deadline closeness + 0.6 x pressure
    fit        = how well the task's difficulty (the student's own rating averaged with the engine's estimate
                 for this student) matches today's energy
    score      = 0.6 x urgency + 0.4 x fit            (same 60/40 weights as the baseline)

Burnout Mode still removes demanding tasks exactly as before. Pure functions; no randomness.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app import heuristic as base
from . import analysis as A
from . import difficulty as D
from . import history as H
from . import workload as W

DEFAULT_DAILY_MINUTES = 120
W_DEADLINE, W_PRESSURE = 0.4, 0.6


@dataclass
class SmartScored:
    task: base.ScorableTask
    score: float
    breakdown: dict = field(default_factory=dict)


def pressure(effort_minutes: float, hours_left: float, daily_minutes: int = DEFAULT_DAILY_MINUTES) -> tuple[float, float]:
    """(pressure 0-1, hours per day needed). Overdue or no time left -> 1.0."""
    if hours_left <= 0:
        return 1.0, float("inf") if effort_minutes else 0.0
    days_left = max(hours_left / 24.0, 1.0 / 24.0)
    available = daily_minutes * days_left
    ratio = effort_minutes / available if available else 1.0
    needed_per_day = effort_minutes / max(days_left, 1.0) / 60.0 if days_left >= 1 else effort_minutes / 60.0
    return round(1.0 - math.exp(-2.0 * ratio), 4), round(needed_per_day, 2)


def rank_smart(tasks: list, energy: int, *, details: dict, now: datetime | None = None, recent_energy: list | None = None,
               extra_burnout: bool = False, skills: dict | None = None, outcomes: list | None = None,
               daily_minutes: int = DEFAULT_DAILY_MINUTES) -> tuple[list, bool]:
    """
    tasks   - list of ScorableTask
    details - {task_id: (description, category)} text used to understand each task
    """
    now = now or datetime.now(timezone.utc)
    skills, outcomes = skills or {}, outcomes or []
    burnout = base.is_burnout_mode(recent_energy or []) or extra_burnout
    cands = [t for t in tasks if t.difficulty <= base.BURNOUT_MAX_DIFFICULTY] if burnout else list(tasks)
    scored = []
    for t in cands:
        desc, cat = details.get(t.id, ("", ""))
        a = A.analyse(t.title, f"{desc} {cat}".strip())
        skill = skills.get(a.skill_kind)
        cal = H.calibration(a.primary, outcomes)
        w = W.estimate(a, skill, {}, cal["factor"], history_n=cal["n"] if cal["basis"] == "kind" else 0)
        # a task the student rated themselves: tiny/unknown size tasks should not outweigh that rating
        diff = D.for_student(a, skill)
        hours_left = (t.deadline - now).total_seconds() / 3600.0
        press, per_day = pressure(w.likely, hours_left, daily_minutes)
        dscore = base.compute_deadline_score(t.deadline, now)
        urgency = W_DEADLINE * dscore + W_PRESSURE * press
        used_difficulty = (t.difficulty + diff.personal) / 2.0
        fit = max(0.0, 1.0 - abs(used_difficulty - energy) / 4.0)
        score = base.DEADLINE_WEIGHT * urgency + base.ENERGY_MATCH_WEIGHT * fit
        scored.append(SmartScored(t, round(score, 4), {
            "deadline_score": round(dscore, 4), "energy_match_score": round(fit, 4),
            "deadline_weight": base.DEADLINE_WEIGHT, "energy_match_weight": base.ENERGY_MATCH_WEIGHT,
            "pressure": press, "effort_minutes": w.likely, "effort_low": w.low, "effort_high": w.high,
            "hours_per_day_needed": per_day, "kind": a.primary, "used_difficulty": round(used_difficulty, 2),
            "effort_confidence": "low" if w.uncertainty >= 0.4 else "medium" if w.uncertainty >= 0.25 else "high",
        }))
    scored.sort(key=lambda s: (-s.score, s.task.id))
    return scored, burnout
