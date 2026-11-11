"""
Step 2 - how hard is it?

Two different questions, kept separate:
  * intrinsic complexity: how demanding the task is for a typical student (kind, scope, technical cues);
  * difficulty for THIS student: the same task adjusted by the student's own skill, whether they have seen the
    topic before, the resources they have, and (when there is enough of it) how earlier tasks felt.

Both come with a range, because with little information the honest answer is a range. Pure functions.
"""
import math
from dataclasses import dataclass, field

from . import taxonomy as T

SKILL_SHIFT = 0.5          # difficulty points per skill step away from 3
PRIOR_SHIFT = {"new": 0.6, "seen": 0.0, "know": -0.4}
RESOURCE_SHIFT = {"none": 0.4, "some": 0.1, "good": -0.2}


@dataclass
class Difficulty:
    intrinsic: float
    personal: float
    low: float
    high: float
    reasons: list = field(default_factory=list)       # short facts the explanation can quote
    skill_known: bool = False
    felt_shift: float = 0.0


def _clamp(x: float, lo: float = 1.0, hi: float = 5.0) -> float:
    return max(lo, min(hi, x))


def intrinsic(analysis) -> tuple[float, float, list]:
    """(level 1-5, spread, reasons) for a typical student."""
    total = sum(k.score for k in analysis.kinds) or 1.0
    base = sum(T.KIND_BASE_DIFFICULTY[k.kind] * k.score for k in analysis.kinds) / total
    if analysis.subjects:                                   # an exam in a hard subject is harder than a general exam
        base = (base + T.KIND_BASE_DIFFICULTY[analysis.subjects[0]]) / 2
    level, reasons = base, []
    size_shift = {"tiny": -0.7, "small": -0.4, "medium": 0.0, "large": 0.4, "huge": 0.8}[analysis.size]
    if size_shift:
        level += size_shift
        reasons.append(f"it looks like a {'bigger' if size_shift > 0 else 'smaller'} piece of work ({analysis.size})")
    if analysis.hard_cues:
        up = min(1.0, 0.4 * len(analysis.hard_cues))
        level += up
        reasons.append(f"it mentions {', '.join(analysis.hard_cues[:2])}, which is demanding")
    if analysis.easy_cues:
        level -= min(0.8, 0.5 * len(analysis.easy_cues))
        reasons.append(f"it sounds introductory ({analysis.easy_cues[0]})")
    if len(analysis.deliverables) >= 5:
        level += 0.3
        reasons.append(f"it has {len(analysis.deliverables)} separate parts")
    if len(analysis.kinds) > 1:
        level += 0.2
        reasons.append("it combines several kinds of work")
    spread = 0.4 + (0.3 if not analysis.scope_known else 0.0) + (0.2 if not analysis.kind_known else 0.0)
    return round(_clamp(level), 2), round(spread, 2), reasons


def for_student(analysis, skill: int | None, answers: dict | None = None, felt_shift: float = 0.0) -> Difficulty:
    answers = answers or {}
    level, spread, reasons = intrinsic(analysis)
    personal = level
    if skill is not None:
        shift = (3 - skill) * SKILL_SHIFT
        personal += shift
        if shift:
            reasons.append(f"you rated your experience {skill}/5, so it is {'harder' if shift > 0 else 'easier'} for you than for an average student")
    prior = answers.get("prior")
    if prior in PRIOR_SHIFT:
        personal += PRIOR_SHIFT[prior]
        if PRIOR_SHIFT[prior]:
            reasons.append("the topic is new to you" if prior == "new" else "you already know this topic")
    res = answers.get("resources")
    if res in RESOURCE_SHIFT:
        personal += RESOURCE_SHIFT[res]
        if res == "none":
            reasons.append("you have no notes or examples to start from")
    if felt_shift:
        personal += felt_shift
        reasons.append("earlier tasks of this kind felt " + ("harder" if felt_shift > 0 else "easier") + " than predicted")
    spread += 0.3 if skill is None else 0.0
    personal = _clamp(personal)
    return Difficulty(intrinsic=level, personal=round(personal, 2), low=round(_clamp(personal - spread / 2), 2),
                      high=round(_clamp(personal + spread / 2), 2), reasons=reasons, skill_known=skill is not None,
                      felt_shift=felt_shift)


def felt_shift_from(outcomes: list, kind: str, k: float = 4.0) -> float:
    """
    How much harder/easier than predicted earlier tasks of this kind felt, shrunk towards 0 when there are few.
    `outcomes` items need .kind, .felt and .predicted_personal (both optional).
    """
    diffs = [o.felt - o.predicted_personal for o in outcomes
             if o.kind == kind and o.felt is not None and o.predicted_personal is not None]
    if len(diffs) < 3:
        return 0.0
    diffs.sort()
    mid = diffs[len(diffs) // 2] if len(diffs) % 2 else (diffs[len(diffs) // 2 - 1] + diffs[len(diffs) // 2]) / 2
    return round(max(-1.0, min(1.0, mid * len(diffs) / (len(diffs) + k))), 2)


def label(level: float) -> str:
    return ["", "very easy", "easy", "medium", "hard", "very hard"][max(1, min(5, round(level)))]
