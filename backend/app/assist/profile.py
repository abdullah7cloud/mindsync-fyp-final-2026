"""
Task profile: from a task's words (and the student's own history) to kind of work, difficulty in general and for THIS
student, a workload range, and the steps ("subtasks") with a study method each.

It reuses the task-aware engine's analysis, difficulty, workload and history modules unchanged. Nothing here talks to a
language model; a language model may only SUGGEST step names or a second opinion on the range (see ai/service.py), and
this module applies those suggestions inside fixed limits.
"""
from dataclasses import asdict
from typing import Optional

from app.taskaware import analysis as A
from app.taskaware import difficulty as D
from app.taskaware import explain as X
from app.taskaware import history as H
from app.taskaware import taxonomy as T
from app.taskaware import workload as W

SELF_RATING_WEIGHT = 0.4          # how much the student's own 1-5 rating counts against the engine's estimate


def stage_to_dict(s) -> dict:
    return {"work_id": s.work_id, "kind": s.kind, "label": s.label, "method": s.method, "minutes": int(s.minutes),
            "deep": bool(s.deep), "session": list(s.session), "breaks": bool(s.breaks)}


def stage_from_dict(d: dict):
    return W.Stage(work_id=d["work_id"], kind=d["kind"], label=d["label"], method=d["method"], minutes=int(d["minutes"]),
                   deep=bool(d["deep"]), session=tuple(d["session"]), breaks=bool(d.get("breaks", True)))


def _confidence(u: float) -> str:
    return "low" if u >= 0.4 else "medium" if u >= 0.25 else "high"


def profile_task(title: str, details: str = "", *, self_difficulty: Optional[int] = None, skills: Optional[dict] = None,
                 outcomes: Optional[list] = None, sessions: Optional[list] = None, answers: Optional[dict] = None,
                 kind_override: Optional[str] = None) -> dict:
    skills, outcomes, sessions, answers = skills or {}, outcomes or [], sessions or [], dict(answers or {})
    if kind_override in T.KINDS:
        answers["kind"] = kind_override
    a = A.analyse(title, details, answers)
    skill = answers.get("skill")
    try:
        skill = int(skill) if skill is not None else None
    except (TypeError, ValueError):
        skill = None
    if skill is None:
        skill = skills.get(a.skill_kind)
    skill = skill if skill in (1, 2, 3, 4, 5) else None
    shift = D.felt_shift_from(outcomes, a.primary)
    diff = D.for_student(a, skill, answers, shift)
    cal = H.calibration(a.primary, outcomes)
    n_kind = cal["n"] if cal["basis"] == "kind" else 0
    w = W.estimate(a, skill, answers, cal["factor"], history_n=n_kind)

    personal = diff.personal
    if self_difficulty in (1, 2, 3, 4, 5):
        personal = round((1 - SELF_RATING_WEIGHT) * personal + SELF_RATING_WEIGHT * float(self_difficulty), 2)
    stages = [stage_to_dict(s) for s in w.stages]
    return {
        "kind": a.primary, "kind_label": T.KINDS[a.primary]["label"], "kind_known": a.kind_known, "skill_kind": a.skill_kind,
        "skill": skill, "size": a.size, "scope_known": a.scope_known, "subjects": a.subjects,
        "intrinsic": round(diff.intrinsic, 2), "personal": round(personal, 2), "personal_low": round(diff.low, 2),
        "personal_high": round(diff.high, 2), "difficulty_label": D.label(personal),
        "difficulty_text": X.difficulty_text(diff, T.KINDS[a.skill_kind]["skill"]),
        "low": int(w.low), "likely": int(w.likely), "high": int(w.high), "raw_likely": int(w.raw_likely),
        "uncertainty": w.uncertainty, "confidence": _confidence(w.uncertainty), "basis": w.basis,
        "workload_text": X.workload_text(w, a, cal), "history": {**cal, "text": X.history_text(cal, T.KINDS[a.primary]["label"])},
        "stages": stages, "understanding": X.understanding(a),
        "uncertainties": X.uncertainty_list(a, skill, answers, set(), True, False, n_kind),
        "_analysis": a,      # kept for the question gate; removed before anything leaves the server
    }


def public(profile: dict) -> dict:
    return {k: v for k, v in profile.items() if not k.startswith("_")}


def widen_with_second_opinion(profile: dict, ai_low: Optional[int], ai_likely: Optional[int], ai_high: Optional[int]) -> dict:
    """
    A language model's estimate is only a second opinion. It may widen the range, but only within [0.5x, 2x] of the
    deterministic likely value, and it never moves the likely value itself.
    """
    base = profile["likely"]
    if not base or not (ai_low or ai_likely or ai_high):
        return profile
    lo_cap, hi_cap = int(base * 0.5), int(base * 2.0)
    vals = [v for v in (ai_low, ai_likely, ai_high) if isinstance(v, int) and v > 0]
    if not vals:
        return profile
    lo = max(lo_cap, min(vals))
    hi = min(hi_cap, max(vals))
    profile["low"] = int(min(profile["low"], lo))
    profile["high"] = int(max(profile["high"], hi))
    profile["second_opinion"] = {"low": lo, "high": hi}
    return profile


def apply_subtasks(profile: dict, subtasks: list) -> dict:
    """
    Replace the generic step names with the names a language model suggested (3-8 steps), keeping the deterministic total.
    Minutes are shared out by the suggested percentages (already validated); methods are the model's short "how" texts.
    """
    if not (3 <= len(subtasks) <= 8) or not profile["stages"]:
        return profile
    total = sum(s["minutes"] for s in profile["stages"])
    shares = [max(1.0, float(s["share_percent"])) for s in subtasks]
    ssum = sum(shares)
    main = max(profile["stages"], key=lambda s: s["minutes"])
    out, used = [], 0
    for i, (st, sh) in enumerate(zip(subtasks, shares)):
        m = int(round(total * sh / ssum / 5.0)) * 5 if i < len(subtasks) - 1 else total - used
        m = max(10, m)
        used += m
        out.append({"work_id": main["work_id"], "kind": main["kind"], "label": st["title"][:120],
                    "method": (st.get("how") or main["method"])[:300], "minutes": m, "deep": main["deep"],
                    "session": list(main["session"]), "breaks": main["breaks"]})
    profile["stages"] = out
    profile["subtasks_source"] = "ai"
    return profile


def stages_after(stages: list, done_minutes: int, remaining_total: int) -> list:
    """
    The steps still to do. Work already done removes the earliest steps first; the rest is rescaled so the steps add up to
    the remaining minutes (the student's own updated estimate wins over the original split).
    """
    if remaining_total <= 0:
        return []
    skip = max(0, done_minutes)
    kept = []
    for s in stages:
        s = dict(s)
        if skip >= s["minutes"]:
            skip -= s["minutes"]
            continue
        s["minutes"] = s["minutes"] - skip
        skip = 0
        kept.append(s)
    if not kept:
        base = stages[-1] if stages else {"work_id": "general_work", "kind": "general", "label": "Finish the task", "method": "Finish what is left.",
                                           "deep": True, "session": [20, 35, 50], "breaks": True}
        kept = [dict(base, label="Finish what is left", minutes=remaining_total)]
    cur = sum(s["minutes"] for s in kept) or 1
    scale = remaining_total / cur
    out, used = [], 0
    for i, s in enumerate(kept):
        m = remaining_total - used if i == len(kept) - 1 else max(5, int(round(s["minutes"] * scale / 5.0)) * 5)
        m = max(5, min(m, remaining_total - used)) if i < len(kept) - 1 else max(5, m)
        used += m
        s["minutes"] = m
        out.append(s)
    return out
