"""
The task-aware planning engine: one pure function, `run(PlanInput)`.

It either returns {"status": "needs_info", "questions": [...]} or {"status": "plan", ...} with the understanding of
the task, difficulty (in general and for this student), the workload as a range, stages with a study method each,
a day-by-day schedule, explanations and the list of things that are still uncertain.

Deterministic: no randomness, no network, no clock (the caller supplies `today`).
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from . import analysis as A
from . import difficulty as D
from . import explain as X
from . import history as H
from . import questions as Q
from . import schedule as S
from . import taxonomy as T
from . import workload as W

DEFAULT_DAILY_MINUTES = 120


@dataclass
class PlanInput:
    title: str
    today: date
    details: str = ""
    deadline: Optional[date] = None
    deadline_hour: Optional[int] = None
    daily_minutes: Optional[int] = None
    today_minutes: Optional[int] = None
    energy: Optional[int] = None
    stress_risk: Optional[str] = None
    answers: dict = field(default_factory=dict)
    skipped: list = field(default_factory=list)
    skills: dict = field(default_factory=dict)          # kind -> 1..5 (saved earlier)
    outcomes: list = field(default_factory=list)        # [history.Outcome]
    sessions: list = field(default_factory=list)        # [history.SessionRecord]


def _int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _confidence(u: float) -> str:
    return "low" if u >= 0.4 else "medium" if u >= 0.25 else "high"


def _label_day(d: date, today: date) -> str:
    delta = (d - today).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return d.strftime("%a %d %b")


def _understanding(a) -> dict:
    return {"text": X.understanding(a),
            "kinds": [{"kind": k.kind, "label": T.KINDS[k.kind]["label"], "score": k.score, "evidence": k.evidence} for k in a.kinds],
            "subjects": a.subjects, "kind_known": a.kind_known, "size": a.size, "size_source": a.size_source,
            "scope_known": a.scope_known, "deliverables": a.deliverables}


def run(p: PlanInput) -> dict:
    answers = dict(p.answers)
    skipped = set(p.skipped)
    a = A.analyse(p.title, p.details, answers)
    skill_kind = a.skill_kind
    skill = _int(answers.get("skill"))
    if skill is None:
        skill = p.skills.get(skill_kind)
    skill = skill if skill in (1, 2, 3, 4, 5) else None
    deadline = p.deadline
    if deadline is None and isinstance(answers.get("deadline"), str):
        try:
            deadline = date.fromisoformat(answers["deadline"][:10])
        except ValueError:
            deadline = None
    daily = _int(answers.get("daily_minutes")) or p.daily_minutes

    qs = Q.next_questions(a, answers=answers, skipped=skipped, skill=skill, has_deadline=deadline is not None,
                          has_hours=daily is not None)
    if qs:
        return {"status": "needs_info", "understanding": _understanding(a),
                "questions": [{"id": q.id, "text": q.text, "type": q.type, "options": [{"value": v, "label": l} for v, l in q.options],
                               "why": q.why, "placeholder": q.placeholder} for q in qs],
                "message": "I need a little more information so I do not guess. You can skip any question, but then the plan will be less certain."}

    # ---- difficulty (general and for this student)
    from .difficulty import felt_shift_from
    shift = felt_shift_from(p.outcomes, a.primary)
    diff = D.for_student(a, skill, answers, shift)

    # ---- workload, calibrated by this student's history for this kind of work
    cal = H.calibration(a.primary, p.outcomes)
    n_hist = sum(1 for o in p.outcomes if o.kind == a.primary)
    w = W.estimate(a, skill, answers, cal["factor"], history_n=cal["n"] if cal["basis"] == "kind" else 0)

    # ---- preferences found for each kind of work in the plan (never carried over to another kind)
    prefs = {}
    for km in a.kinds:
        baseline = max((s.session[1] for s in w.stages if s.kind == km.kind), default=40)
        pref = H.preferred_session(km.kind, p.sessions, baseline)
        if pref:
            prefs[km.kind] = pref

    hours_defaulted = daily is None
    daily = daily or DEFAULT_DAILY_MINUTES
    sched = S.build(w.stages, today=p.today, deadline=deadline, deadline_hour=p.deadline_hour, daily_minutes=daily,
                    today_minutes=p.today_minutes, personal_difficulty=diff.personal, energy=p.energy,
                    stress_risk=p.stress_risk, preferences=prefs)

    stages_out = []
    for i, st in enumerate(w.stages):
        stages_out.append({"index": i, "label": st.label, "work_id": st.work_id, "kind": st.kind, "minutes": st.minutes,
                           "method": st.method, "deep": st.deep})
    for day in sched["days"]:
        day["label"] = _label_day(date.fromisoformat(day["date"]), p.today)
        for s in day["sessions"]:
            s["method"] = w.stages[s["stage_index"]].method
            s["text"] = X.session_text(s["stage_label"], s["minutes"], s["why_length"], s["break_after"])

    uncertain = X.uncertainty_list(a, skill, answers, skipped, deadline is not None, hours_defaulted, n_hist)
    advice = []
    if w.likely == 0:
        advice.append("Everything is already finished, so there is nothing to schedule.")
    elif deadline is not None:
        cap = sched["capacity_minutes"]
        if not sched["feasible"]:
            advice.append(f"This does not fit before the deadline at {daily // 60 if daily >= 60 else daily}{' h' if daily >= 60 else ' min'} a day: "
                          f"{X._hours(sched['shortfall_minutes'])} would be left over. You would need about {X._hours(sched['needed_per_day'])} a day, "
                          "or a smaller scope, or more time.")
        elif w.high > cap:
            advice.append(f"It fits if the task takes the likely time, but if it takes the high end ({X._hours(w.high)}) it will not. "
                          "Starting today leaves room for that.")
        else:
            spare = (date.fromisoformat(sched["last_day"]) - date.fromisoformat(sched["finish_date"])).days if sched["finish_date"] else 0
            advice.append(f"It fits: the work is planned to finish on {sched['finish_date']}"
                          + (f", leaving {spare} spare day{'s' if spare != 1 else ''} before the deadline." if spare > 0 else ", on the last day available."))
    first = None
    if sched["days"]:
        s0 = sched["days"][0]["sessions"][0]
        first = {"day": sched["days"][0]["label"], "label": s0["stage_label"], "minutes": s0["minutes"], "method": s0["method"]}

    session_why = {}
    for day in sched["days"]:
        for s in day["sessions"]:
            session_why.setdefault(s["stage_label"], s["why_length"])
    return {
        "status": "plan",
        "understanding": _understanding(a),
        "difficulty": {"intrinsic": diff.intrinsic, "for_you": diff.personal, "low": diff.low, "high": diff.high,
                       "label": D.label(diff.personal), "skill": skill, "skill_known": diff.skill_known,
                       "text": X.difficulty_text(diff, T.KINDS[skill_kind]["skill"])},
        "workload": {"likely": w.likely, "low": w.low, "high": w.high, "raw_likely": w.raw_likely, "basis": w.basis,
                     "uncertainty": w.uncertainty, "confidence": _confidence(w.uncertainty), "already_done": w.already_done,
                     "text": X.workload_text(w, a, cal), "stages": stages_out,
                     "history": {**cal, "text": X.history_text(cal, T.KINDS[a.primary]["label"])}},
        "schedule": {k: sched[k] for k in ("days", "feasible", "shortfall_minutes", "needed_per_day", "finish_date", "last_day",
                                           "buffer_days", "days_available", "capacity_minutes", "total_minutes", "unscheduled", "stats")},
        "session_reasons": session_why,
        "preferences_used": {k: v for k, v in prefs.items()},
        "uncertainties": uncertain,
        "advice": advice,
        "first_step": first,
        "inputs_used": {"kind": a.primary, "skill_kind": skill_kind, "raw_likely_minutes": w.raw_likely,
                        "predicted_personal": diff.personal, "daily_minutes": daily, "daily_assumed": hours_defaulted},
        "limits": "Estimates come from the words you gave and your own history. I have not read any course material, "
                  "so the steps are general methods for this kind of work, not instructions from your lecturer.",
    }
