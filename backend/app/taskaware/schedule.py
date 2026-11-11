"""
Step 5 - turn the stages into sessions on real days, under constraints.

Constraints that are always respected:
  * every session lies on a day from today up to the last day before the deadline;
  * the minutes planned on a day never exceed the hours the student has that day (today can be set separately);
  * deep-focus work per day stays below a per-kind limit;
  * stages keep their order, and a "review again after a gap" stage is placed on a later day than the work it
    reviews whenever the calendar allows it.
If the work does not fit, nothing is squeezed in silently: the plan reports the shortfall and the hours per day that
would be needed.

Session length depends on the kind of work, the student's own history for that kind, how hard it is for them and the
energy / wellbeing today. Breaks depend on how long the session was and how long the student has been concentrating
(none after short or administrative blocks). No randomness.
"""
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from . import taxonomy as T

MIN_SESSION = 10
LONG_FOCUS_MINUTES = 100        # after this much deep work without a long break, the next break is longer
HORIZON_WITHOUT_DEADLINE = 14


@dataclass
class Session:
    stage_index: int
    stage_label: str
    kind: str
    work_id: str
    minutes: int
    deep: bool
    part: int
    parts: int
    break_after: int = 0
    why_length: str = ""


def _round5(x: float) -> int:
    return max(MIN_SESSION, int(round(x / 5.0)) * 5)


def session_plan(stage, personal_difficulty: float, energy: Optional[int], stress_risk: Optional[str],
                 preferred: Optional[dict], today: bool) -> tuple[int, int, str]:
    """(ideal minutes, longest minutes, short reason) for one stage."""
    lo, ideal, hi = stage.session
    why = f"usual length for '{stage.label.lower()}'"
    if stage.kind in ("mathematics", "exam", "reading") and personal_difficulty >= 4.0:
        ideal, hi = min(ideal, 40), min(hi, 45)
        why = "shorter blocks because this is hard for you and hard topics tire you faster"
    if preferred and preferred.get("minutes"):
        ideal = max(MIN_SESSION, min(preferred["minutes"], hi + 15))
        hi = max(hi, ideal)
        why = f"your own {preferred['band'][0]}-{preferred['band'][1]} minute {T.KINDS[stage.kind]['label'].lower()} sessions were finished more often"
    if today:
        if energy is not None and energy <= 2:
            ideal, hi = int(ideal * 0.7), int(hi * 0.7)
            why = "shorter because your energy is low today"
        if stress_risk == "High":
            ideal, hi = min(ideal, 25), min(hi, 30)
            why = "short and gentle because your wellbeing check was high"
        elif stress_risk == "Medium":
            ideal, hi = min(ideal, 40), min(hi, 45)
    return max(MIN_SESSION, ideal), max(MIN_SESSION, hi), why


def _split(minutes: int, ideal: int, longest: int) -> list:
    if minutes <= longest * 1.15:
        return [minutes]
    n = max(2, int(round(minutes / ideal)))
    while math.ceil(minutes / n) > longest:
        n += 1
    base = _round5(minutes / n)
    out = [base] * (n - 1)
    out.append(max(MIN_SESSION, minutes - base * (n - 1)))      # the last part ends exactly where the stage ends
    return out


def break_after(session: Session, deep_since_break: int, low_load: bool) -> int:
    """Minutes of break that should follow this session (0 = none needed)."""
    minutes = session.minutes
    if deep_since_break >= LONG_FOCUS_MINUTES:
        return 20
    stage_breaks = T.WORKS[session.work_id].breaks
    if not stage_breaks and minutes < 45:
        return 0
    if minutes >= 40:
        return 10
    if minutes >= 25 or (low_load and minutes >= 20):
        return 5 if not low_load else 10
    return 0


def build(stages: list, *, today: date, deadline: Optional[date], deadline_hour: Optional[int], daily_minutes: int,
          today_minutes: Optional[int], personal_difficulty: float, energy: Optional[int], stress_risk: Optional[str],
          preferences: Optional[dict] = None) -> dict:
    preferences = preferences or {}
    # ---- days that can be used
    if deadline is None:
        last_day = today + timedelta(days=HORIZON_WITHOUT_DEADLINE - 1)
    else:
        last_day = deadline if (deadline_hour is None or deadline_hour >= 12) else deadline - timedelta(days=1)
    n_days = max(0, (last_day - today).days + 1)
    days = [today + timedelta(days=i) for i in range(n_days)]
    cap = {d: daily_minutes for d in days}
    low_load = False
    if days:
        cap[days[0]] = daily_minutes if today_minutes is None else today_minutes
        if energy is not None and energy <= 2:
            cap[days[0]] = int(cap[days[0]] * 0.6)
            low_load = True
        if stress_risk == "High":
            cap[days[0]] = int(cap[days[0]] * 0.6)
            low_load = True
        elif stress_risk == "Medium":
            cap[days[0]] = int(cap[days[0]] * 0.85)
    buffer_days = 0 if n_days <= 3 else (1 if n_days <= 8 else 2)
    if deadline is None:
        buffer_days = 0
    target_days = days[: max(1, n_days - buffer_days)] if days else []

    # ---- sessions in stage order
    sessions: list[Session] = []
    today_cut: dict[int, tuple] = {}
    for si, st in enumerate(stages):
        ideal, hi, why = session_plan(st, personal_difficulty, energy, stress_risk, preferences.get(st.kind), today=True)
        ideal_f, hi_f, why_f = session_plan(st, personal_difficulty, None, None, preferences.get(st.kind), today=False)
        limit = max(MIN_SESSION, daily_minutes)            # a session must fit inside one day
        parts = _split(st.minutes, min(ideal_f, limit), min(hi_f, limit))
        for pi, m in enumerate(parts):
            sessions.append(Session(si, st.label, st.kind, st.work_id, m, st.deep, pi + 1, len(parts), why_length=why_f))
        if (ideal, hi) != (ideal_f, hi_f):                 # today looks different (low energy / wellbeing): remember how
            today_cut[si] = (ideal, hi, why)
    total = sum(s.minutes for s in sessions)

    # ---- place sessions on days (first spread evenly; if that leaves work over, try again filling days up to the limits)
    def attempt(pace_on: bool):
        import copy
        placed: dict[date, list] = {d: [] for d in days}
        used = {d: 0 for d in days}
        deep_used = {d: {} for d in days}
        unplaced: list[Session] = []
        day_i = 0
        last_day_of_stage: dict[int, int] = {}
        remaining = total

        def deep_limit(kind):
            return T.KINDS[kind]["deep_limit"]

        def split_off(s: Session, first: int) -> Session:
            """Cut `first` minutes off the front of s; return the rest as a new session that follows it."""
            rest = Session(s.stage_index, s.stage_label, s.kind, s.work_id, s.minutes - first, s.deep, s.part + 1, s.parts + 1,
                           why_length=s.why_length)
            s.minutes, s.parts = first, s.parts + 1
            return rest

        use_days = days
        queue = [copy.copy(x) for x in sessions]
        qi = 0
        while qi < len(queue):
            s = queue[qi]
            qi += 1
            earliest = 0
            if s.work_id == "exam_spaced" and s.stage_index - 1 in last_day_of_stage:
                earliest = min(last_day_of_stage[s.stage_index - 1] + 1, len(use_days) - 1) if use_days else 0
            di = max(day_i, earliest)
            placed_ok = False
            while di < len(use_days):
                d = use_days[di]
                # today may need shorter sessions (low energy, wellbeing): cut the session before placing it
                if di == 0 and s.stage_index in today_cut:
                    t_ideal, t_hi, t_why = today_cut[s.stage_index]
                    if s.minutes > t_hi:
                        first = _round5(t_ideal)
                        if s.minutes - first >= 5:
                            queue.insert(qi, split_off(s, first))
                            s.why_length = t_why
                    else:
                        s.why_length = t_why
                days_left_target = max(1, len(target_days) - di)
                # pace: spread large work evenly over the target days; small work is finished early
                pace = max(MIN_SESSION, int(math.ceil(remaining / days_left_target / 5.0)) * 5) if di < len(target_days) else cap[d]
                budget = min(cap[d], max(pace, s.minutes))
                if di == len(use_days) - 1 or not pace_on:
                    budget = cap[d]              # last day available: pacing no longer matters, only the hours
                room = cap[d] - used[d]
                dl = deep_used[d].get(s.kind, 0)
                fits_deep = (not s.deep) or dl + s.minutes <= deep_limit(s.kind) or dl == 0
                if s.minutes <= room and used[d] + s.minutes <= max(budget, 0) and fits_deep:
                    placed[d].append(s)
                    used[d] += s.minutes
                    if s.deep:
                        deep_used[d][s.kind] = dl + s.minutes
                    last_day_of_stage[s.stage_index] = di
                    day_i = max(day_i, di)
                    remaining -= s.minutes
                    placed_ok = True
                    break
                # use a useful leftover of this day by placing the first part of the session here
                if 25 <= room < s.minutes and s.minutes - room >= 5 and used[d] < budget and fits_deep:
                    first = (room // 5) * 5
                    queue.insert(qi, split_off(s, first))
                    continue
                di += 1
            if not placed_ok:
                unplaced.append(s)
                remaining -= s.minutes


        return placed, unplaced

    placed, unplaced = attempt(True)
    if unplaced:
        placed, unplaced = attempt(False)

    # ---- breaks
    out_days = []
    for d in days:
        deep_since = 0
        items = placed[d]
        for i, s in enumerate(items):
            if s.deep:
                deep_since += s.minutes
            nxt = items[i + 1] if i + 1 < len(items) else None
            s.break_after = break_after(s, deep_since, low_load and d == days[0]) if nxt else 0
            if s.break_after >= 20 or (nxt is None):
                deep_since = 0
            elif s.break_after >= 10:
                deep_since = max(0, deep_since - 30)
        if items:
            out_days.append({"date": d.isoformat(), "total_minutes": sum(s.minutes for s in items),
                             "sessions": [s.__dict__ for s in items]})
    short = sum(s.minutes for s in unplaced)
    study_days = [x for x in out_days]
    finish = study_days[-1]["date"] if study_days else None
    all_sessions = [s for d in days for s in placed[d]]
    window_study = sum(cap.values())
    needed_per_day = int(math.ceil(total / max(1, n_days) / 5.0)) * 5 if n_days else total
    return {
        "days": out_days,
        "feasible": not unplaced and bool(all_sessions or total == 0),
        "shortfall_minutes": short,
        "needed_per_day": needed_per_day,
        "finish_date": finish,
        "last_day": last_day.isoformat() if days else None,
        "buffer_days": buffer_days,
        "days_available": n_days,
        "capacity_minutes": window_study,
        "total_minutes": total,
        "unscheduled": [s.__dict__ for s in unplaced],
        "stats": {
            "sessions": len(all_sessions),
            "distinct_lengths": len({s.minutes for s in all_sessions}),
            "breaks": sum(1 for s in all_sessions if s.break_after),
            "sessions_without_break": sum(1 for s in all_sessions if not s.break_after),
            "break_lengths": sorted({s.break_after for s in all_sessions if s.break_after}),
        },
    }
