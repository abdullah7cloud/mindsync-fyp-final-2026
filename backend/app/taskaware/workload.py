"""
Step 3 - how much work is it, in total?

Returns the TOTAL effort (focused minutes) as a range, plus the stages the work naturally splits into. This is
deliberately not the length of one study session: sessions, breaks, days left and available hours are decided
later by the scheduler.

Effort comes from, in order of preference:
  1. counts in the text (2,000 words, 12 slides, 20 questions ...) times typical minutes per unit;
  2. the number of listed deliverables times typical minutes per deliverable;
  3. the size of the task ("project", "exercise" ...) times the usual effort for that kind of work.
It is then scaled by the student's skill, whether the topic is new and the resources they have, and finally by the
student's own history (history.py). Base numbers are the author's design assumptions and are only ranges.
"""
from dataclasses import dataclass, field

from . import taxonomy as T

SKILL_MULT = {1: 1.6, 2: 1.3, 3: 1.0, 4: 0.85, 5: 0.7}
PRIOR_MULT = {"new": 1.2, "seen": 1.0, "know": 0.85}
RESOURCE_MULT = {"none": 1.15, "some": 1.05, "good": 0.95}
# how well the student says they already understand THIS topic (1 not yet ... 4 very well). Self-reported, so the effect is kept small
GRASP_MULT = {1: 1.2, 2: 1.1, 3: 1.0, 4: 0.9}
PER_DELIVERABLE = {"programming": 90, "writing": 60, "data": 50, "mathematics": 25, "exam": 70, "reading": 30,
                   "presentation": 45, "general": 45, "admin": 10}
PROGRESS = {"none": 0.0, "some": 0.25, "half": 0.5, "most": 0.8, "done": 1.0}
MIN_STAGE = 12


@dataclass
class Stage:
    work_id: str
    kind: str
    label: str
    method: str
    minutes: int
    deep: bool
    session: tuple
    breaks: bool


@dataclass
class Workload:
    raw_likely: int                 # estimate before the student's history is applied
    likely: int
    low: int
    high: int
    uncertainty: float
    basis: str                      # counts | deliverables | size
    stages: list = field(default_factory=list)
    already_done: float = 0.0
    parts: dict = field(default_factory=dict)       # kind -> minutes
    multipliers: dict = field(default_factory=dict)


def _round5(x: float) -> int:
    return max(5, int(round(x / 5.0)) * 5)


def parse_progress(value) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value) / 100.0))
    if isinstance(value, str):
        v = value.strip().lower().rstrip("%")
        if v in PROGRESS:
            return PROGRESS[v]
        try:
            return max(0.0, min(1.0, float(v) / 100.0))
        except ValueError:
            return 0.0
    return 0.0


def _kind_effort(kind: str, analysis, primary: bool) -> tuple[float, str]:
    parts = []
    for number, unit in analysis.counts:
        per = T.UNIT_MINUTES.get((kind, unit))
        if per is not None:
            parts.append(number * per)
    used = bool(parts)
    # "chapters 4 to 6, about 90 pages" is one piece of reading described twice: take the larger, do not add them
    counted = max(parts) if kind in ("reading", "exam", "presentation") and parts else sum(parts)
    if used:
        if kind == "presentation":
            counted *= 1.0           # slide minutes already include a share of rehearsal
        return counted, "counts"
    by_size = T.KINDS[kind]["base"] * T.SIZE_MULT[analysis.size]
    n = len(analysis.deliverables)
    if n >= 2:
        by_items = n * PER_DELIVERABLE.get(kind, 45)
        if by_items > by_size:
            return by_items, "deliverables"
        if analysis.size_source == "default":
            # the size is unknown, so a short list must not shrink the task below half of the usual effort for this kind of work:
            # under-estimating is the harmful direction (the student under-plans)
            return max(by_items, by_size * 0.5), "deliverables"
    return (by_size if primary else by_size * 0.5), "size"


def _merge_small(stages: list) -> list:
    out = []
    for s in stages:
        if out and s.minutes < MIN_STAGE:
            out[-1].minutes += s.minutes
        else:
            out.append(s)
    if len(out) > 1 and out[0].minutes < MIN_STAGE:
        out[1].minutes += out[0].minutes
        out = out[1:]
    return out


def _stages_for(kind: str, minutes: float) -> list:
    spec = T.KINDS[kind]["stages"]
    if minutes <= 30 and kind != "admin":
        main = max(spec, key=lambda s: s[1])[0]
        spec = [(main, 1.0)]
    stages = []
    for work_id, share in spec:
        w = T.WORKS[work_id]
        stages.append(Stage(work_id, kind, w.label, w.method, int(round(minutes * share)), w.deep, w.session, w.breaks))
    return _merge_small(stages)


def estimate(analysis, skill: int | None, answers: dict | None, calibration_factor: float = 1.0, history_n: int = 0) -> Workload:
    answers = answers or {}
    total_score = sum(k.score for k in analysis.kinds) or 1.0
    efforts, basis = {}, "size"
    for i, km in enumerate(analysis.kinds):
        e, b = _kind_effort(km.kind, analysis, primary=(i == 0))
        efforts[km.kind] = e
        if i == 0:
            basis = b
    coordination = 1.0 + 0.15 * (len(efforts) - 1)
    mult = {"skill": SKILL_MULT.get(skill, 1.0), "prior": PRIOR_MULT.get(answers.get("prior"), 1.0),
            "resources": RESOURCE_MULT.get(answers.get("resources"), 1.0), "coordination": coordination,
            "grasp": GRASP_MULT.get(answers.get("grasp"), 1.0) if isinstance(answers.get("grasp"), int) and not isinstance(answers.get("grasp"), bool) else 1.0}
    scale = mult["skill"] * mult["prior"] * mult["resources"] * coordination * mult["grasp"]
    raw_parts = {k: v * scale for k, v in efforts.items()}
    raw_total = sum(raw_parts.values())
    done = parse_progress(answers.get("progress"))
    parts = {k: v * calibration_factor for k, v in raw_parts.items()}

    stages = []
    for km in analysis.kinds:
        stages += _stages_for(km.kind, parts[km.kind])
    # work already finished removes the earliest stages first (the work is done in order)
    skip = sum(s.minutes for s in stages) * done
    kept = []
    for s in stages:
        if skip >= s.minutes:
            skip -= s.minutes
            continue
        s.minutes = int(round(s.minutes - skip))
        skip = 0
        kept.append(s)
    for s in kept:
        s.minutes = _round5(s.minutes)
    remaining = sum(s.minutes for s in kept)

    u = 0.18
    u += 0.12 if not analysis.scope_known else 0.0
    u += 0.10 if skill is None else 0.0
    u += 0.10 if not analysis.kind_known else 0.0
    u += 0.08 if analysis.size_source == "default" and basis == "size" else 0.0
    u -= 0.10 * min(1.0, history_n / 8.0)
    u = round(max(0.12, min(0.6, u)), 2)
    likely = _round5(remaining) if remaining else 0
    return Workload(raw_likely=_round5(raw_total * (1 - done)) if raw_total * (1 - done) > 0 else 0, likely=likely,
                    low=_round5(likely * (1 - 0.8 * u)) if likely else 0, high=_round5(likely * (1 + 1.6 * u)) if likely else 0,
                    uncertainty=u, basis=basis, stages=kept, already_done=done,
                    parts={k: int(round(v)) for k, v in parts.items()}, multipliers=mult)
