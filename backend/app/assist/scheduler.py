"""
The multi-task scheduler. Pure, deterministic code: no network, no randomness, no clock (the caller passes `now`).

What it guarantees (and what the tests check):
  * a day never gets more minutes than that day's capacity (study days, weekday/weekend hours, energy, gentle mode);
  * every minute is placed on or before the last usable day of its task, whenever the whole set is feasible;
  * if it is NOT feasible nothing is squeezed in silently: the shortfall, the task that breaks first and concrete,
    verified alternatives are reported.

Method (in one paragraph): feasibility is the earliest-deadline-first test. For every deadline d, the work whose deadline is
<= d must fit in the capacity up to d; the largest violation is the shortfall. Placement then goes day by day. Each task gets its
"pacing share" of the day (its remaining work spread over the capacity that is left before its deadline) and, if the
test for tomorrow would otherwise fail, at least the amount that must be done today. Earliest deadline is served first.
That keeps work even ("even" pacing) or front-loaded ("early") without ever making a feasible set infeasible.
"""
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from app.taskaware import schedule as S
from app.taskaware import taxonomy as T

from .profile import stage_from_dict
from .settings_schema import StudySettings

MAX_HORIZON = 60
DAY_START_HOUR, DAY_END_HOUR = 8, 22
WINDOW_START = {"morning": 9 * 60, "afternoon": 14 * 60, "evening": 19 * 60, "night": 21 * 60}
PERIOD_ORDER = ["morning", "afternoon", "evening", "night"]
LAST_USABLE_HOUR = 18                  # a deadline before 18:00 means that day itself is not planned
ENERGY_TODAY_FACTOR = {1: 0.6, 2: 0.8}
GENTLE_FACTOR = 0.8


@dataclass
class PlanTask:
    id: str
    title: str
    deadline: datetime                 # timezone-aware, in the student's time zone
    remaining: int                     # minutes still to do (likely)
    remaining_high: int = 0            # same, at the high end of the range (0 = use `remaining`)
    kind: str = "general"
    difficulty: float = 3.0            # difficulty for this student, 1-5
    stages: list = field(default_factory=list)
    priority: int = 2
    est_likely: int = 0


def _r5(x: float) -> int:
    return int(x // 5) * 5


def _ceil5(x: float) -> int:
    return int(math.ceil(x / 5.0)) * 5


def _last_usable_date(deadline: datetime) -> date:
    d = deadline.date()
    return d if deadline.hour + deadline.minute / 60.0 >= LAST_USABLE_HOUR else d - timedelta(days=1)


def gentle_state(settings: StudySettings, energy: Optional[int], stress: Optional[str]) -> dict:
    by_energy = energy is not None and energy <= 2
    by_stress = stress == "High"
    if settings.gentle_mode == "off":
        return {"on": False, "days": 0, "reason": None}
    if settings.gentle_mode == "always":
        return {"on": True, "days": MAX_HORIZON, "reason": "always"}
    if by_stress:
        return {"on": True, "days": 7, "reason": "wellbeing"}
    if by_energy:
        return {"on": True, "days": 3, "reason": "energy"}
    return {"on": False, "days": 0, "reason": None}


def day_capacities(settings: StudySettings, now: datetime, n_days: int, *, energy: Optional[int], stress: Optional[str],
                   studied_today: int = 0, today_minutes: Optional[int] = None, extra_per_day: int = 0,
                   all_days: bool = False) -> list:
    today = now.date()
    g = gentle_state(settings, energy, stress)
    caps = []
    for k in range(n_days):
        d = today + timedelta(days=k)
        wd = d.weekday()
        base = settings.weekend_minutes if wd >= 5 else settings.weekday_minutes
        studying = all_days or wd in settings.study_days
        if str(wd) in settings.day_minutes:          # the student set this weekday on its own
            base = settings.day_minutes[str(wd)]
            studying = all_days or (wd in settings.study_days and base > 0)
        c = float(base + (extra_per_day if base > 0 else 0)) if studying else 0.0
        if g["on"] and k < g["days"]:
            c *= GENTLE_FACTOR
        if k == 0:
            if today_minutes is not None:
                c = float(today_minutes)
            else:
                hour = now.hour + now.minute / 60.0
                left = max(0.0, min(1.0, (DAY_END_HOUR - hour) / float(DAY_END_HOUR - DAY_START_HOUR)))
                c = c * left
                if settings.gentle_mode != "off" and energy in ENERGY_TODAY_FACTOR:
                    c *= ENERGY_TODAY_FACTOR[energy]
                c = max(0.0, min(c, float(base if studying else 0) - studied_today)) if c > 0 else 0.0
        caps.append(_r5(c))
    return caps


def _offsets(tasks: list, now: datetime, buffer_days: int, n_cap: int = MAX_HORIZON) -> dict:
    """Last day (as an offset from today) on which each task may be worked on. Also returns flags."""
    today = now.date()
    out = {}
    for t in tasks:
        overdue = t.deadline <= now
        last = _last_usable_date(t.deadline)
        raw = (last - today).days
        flag = "overdue" if overdue else ("due_today" if raw < 0 else None)
        real = max(0, min(raw, n_cap - 1))
        buffered = max(0, real - buffer_days)
        out[t.id] = {"real": real, "buffered": buffered, "flag": flag, "beyond": raw > n_cap - 1}
    return out


def _prefix(caps: list) -> list:
    p = [0]
    for c in caps:
        p.append(p[-1] + c)
    return p


def edf_shortfall(items: list, caps: list) -> tuple:
    """items: [(last_offset, minutes, id)]. Returns (largest shortfall, id of the earliest task whose deadline cannot be met)."""
    pre = _prefix(caps)
    demand, worst, first = 0, 0, None
    for last, minutes, tid in sorted(items, key=lambda x: (x[0], str(x[2]))):
        demand += minutes
        supply = pre[min(last + 1, len(caps))]
        if demand - supply > 0 and first is None:
            first = tid                      # the first deadline (in time order) that cannot be met
        worst = max(worst, demand - supply)
    return worst, first


def _order_key(t: PlanTask, last: int):
    return (last, -t.priority, -t.difficulty, t.id)


def _allocate(tasks: list, caps: list, last_of: dict, pacing: str, soft_of: Optional[dict] = None) -> tuple:
    """Day-by-day minutes for each task. Returns ({day: {task_id: minutes}}, {task_id: leftover})."""
    n = len(caps)
    pre = _prefix(caps)
    soft_of = soft_of or last_of            # the day we would LIKE to finish by (the buffered one); last_of is the hard limit
    rem = {t.id: t.remaining for t in tasks}
    order = sorted(tasks, key=lambda t: _order_key(t, last_of[t.id]))
    plan = {}
    for k in range(n):
        c_left = caps[k]
        if c_left <= 0:
            continue
        cum = allocated = 0
        alloc = {}
        for t in order:
            if rem[t.id] <= 0 or last_of[t.id] < k:
                continue
            L = last_of[t.id]
            cum += rem[t.id]
            supply_after = pre[min(L + 1, n)] - pre[k + 1]
            must = max(0, cum - supply_after)
            S_ = min(soft_of[t.id], L)
            if pacing == "early" or k > S_:
                share = rem[t.id]
            else:
                denom = pre[min(S_ + 1, n)] - pre[k]
                share = rem[t.id] * caps[k] / denom if denom > 0 else rem[t.id]
            want = max(share, must - allocated)
            give = min(rem[t.id], c_left, _ceil5(want))
            if 0 < give < 10 and rem[t.id] > give:
                give = min(rem[t.id], c_left, 10) if must - allocated > 0 else 0
            if give > 0:
                alloc[t.id] = give
                allocated += give
                c_left -= give
                rem[t.id] -= give
        if alloc:
            plan[k] = alloc
    return plan, rem


def _check(tasks: list, settings: StudySettings, now: datetime, *, energy, stress, studied_today, today_minutes, n_days,
           extra_per_day=0, all_days=False, scale: Optional[dict] = None, extend: Optional[dict] = None,
           drop: tuple = (), buffer_days: Optional[int] = None, high: bool = False) -> tuple:
    caps = day_capacities(settings, now, n_days, energy=energy, stress=stress, studied_today=studied_today,
                          today_minutes=today_minutes, extra_per_day=extra_per_day, all_days=all_days)
    offs = _offsets(tasks, now, settings.buffer_days if buffer_days is None else buffer_days, n_days)
    items = []
    for t in tasks:
        if t.id in drop:
            continue
        last = offs[t.id]["buffered" if (buffer_days is None and settings.buffer_days) or buffer_days else "real"]
        if buffer_days == 0:
            last = offs[t.id]["real"]
        last = min(n_days - 1, last + (extend or {}).get(t.id, 0))
        m = (t.remaining_high or t.remaining) if high else t.remaining
        m = _ceil5(m * (scale or {}).get(t.id, 1.0))
        items.append((last, m, t.id))
    return edf_shortfall(items, caps)


def _n_days(tasks: list, now: datetime) -> int:
    far = max((max(0, (_last_usable_date(t.deadline) - now.date()).days) for t in tasks), default=0)
    return max(1, min(MAX_HORIZON, far + 1))


def _fmt_hm(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h} h {m} min"
    return f"{h} h" if h else f"{m} min"


def _label_day(d: date, today: date) -> str:
    delta = (d - today).days
    return "Today" if delta == 0 else "Tomorrow" if delta == 1 else d.strftime("%a %d %b")


def _clock(minute_of_day: int) -> str:
    minute_of_day = max(0, min(minute_of_day, 23 * 60 + 59))
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def _scaled_session(plan_tuple: tuple, style: str, bias: float = 1.0) -> tuple:
    ideal, hi, why = plan_tuple
    if bias != 1.0:
        ideal, hi = max(S.MIN_SESSION, int(ideal * bias)), max(S.MIN_SESSION, int(hi * bias))
        why = "adjusted because you told me similar blocks felt " + ("too long" if bias < 1 else "too short")
    if style == "short":
        ideal, hi, why = max(S.MIN_SESSION, int(ideal * 0.7)), max(S.MIN_SESSION, int(hi * 0.75)), "shorter blocks, as you chose in Settings"
    elif style == "long":
        ideal, hi, why = int(ideal * 1.3), int(hi * 1.3), "longer blocks, as you chose in Settings"
    return ideal, hi, why


def _break_minutes(raw: int, style: str) -> int:
    if raw <= 0:
        return 0
    mult = {"short": 0.6, "standard": 1.0, "long": 1.5}[style]
    return max(5, int(round(raw * mult / 5.0)) * 5)


def _sessionise(day_alloc: dict, queues: dict, by_id: dict, k: int, now: datetime, settings: StudySettings, *, energy, stress,
                prefs: dict, boundary_log: dict) -> list:
    today = now.date()
    d = today + timedelta(days=k)
    ordered = list(day_alloc)
    easy_first = k == 0 and energy is not None and energy <= 2 and settings.gentle_mode != "off"
    ordered.sort(key=lambda tid: (by_id[tid].difficulty if easy_first else -by_id[tid].difficulty, by_id[tid].deadline, tid))
    sessions, deep_since_break = [], 0
    for tid in ordered:
        t = by_id[tid]
        minutes = day_alloc[tid]
        q = queues[tid]
        mine, carry = [], 0
        while minutes > 0 and q:
            stage, left = q[0]
            take = min(minutes, left)
            q[0][1] -= take
            minutes -= take
            stage_obj = stage_from_dict(stage)
            ideal, hi, why = _scaled_session(
                S.session_plan(stage_obj, t.difficulty, energy if settings.gentle_mode != "off" else None,
                               stress if settings.gentle_mode != "off" else None, prefs.get(stage["kind"]) if stage["kind"] != "_bias" else None, k == 0),
                settings.session_style, prefs.get("_bias", {}).get(stage["kind"], 1.0))
            if take < S.MIN_SESSION and stage["kind"] != "admin" and (mine or minutes > 0):
                # a 5-minute leftover of a stage is not a useful block: it joins a neighbouring session of the same task and day
                if mine:
                    mine[-1]["minutes"] += take
                else:
                    carry += take
                if q[0][1] <= 0:
                    boundary_log.setdefault(tid, []).append({"label": stage["label"], "date": d.isoformat()})
                    q.pop(0)
                continue
            take += carry
            carry = 0
            pieces = S._split(take, ideal, max(hi, ideal)) if take >= S.MIN_SESSION else [take]
            for i, pm in enumerate(pieces):
                mine.append({"task_id": tid, "title": t.title, "stage_label": stage["label"], "method": stage["method"],
                                 "kind": stage["kind"], "work_id": stage["work_id"], "minutes": pm, "deep": stage["deep"],
                                 "part": i + 1, "parts": len(pieces), "why_length": why, "break_after": 0,
                                 "_stage_obj": stage_obj})
            if q[0][1] <= 0:
                boundary_log.setdefault(tid, []).append({"label": stage["label"], "date": d.isoformat()})
                q.pop(0)
        if carry and mine:                       # nothing came after it today: it joins the last block
            mine[-1]["minutes"] += carry
        elif carry:                              # nothing else to join: keep the minutes as their own short block
            mine.append({"task_id": tid, "title": t.title, "stage_label": stage["label"], "method": stage["method"],
                         "kind": stage["kind"], "work_id": stage["work_id"], "minutes": carry, "deep": stage["deep"],
                         "part": 1, "parts": 1, "why_length": why, "break_after": 0, "_stage_obj": stage_obj})
        sessions.extend(mine)
    low_load = (energy is not None and energy <= 2) or stress == "High"
    clock = None
    pref = settings.preferred_time
    if pref in WINDOW_START and pref in settings.unavailable_periods:        # the preferred part of the day is blocked: use the next free one after it
        i = PERIOD_ORDER.index(pref)
        pref = next((p for p in PERIOD_ORDER[i + 1:] + PERIOD_ORDER[:i] if p not in settings.unavailable_periods), None)
    elif pref == "flexible" and settings.unavailable_periods and len(settings.unavailable_periods) < 4:
        pref = next((p for p in PERIOD_ORDER if p not in settings.unavailable_periods), None)
    if pref in WINDOW_START:
        clock = WINDOW_START[pref]
        if k == 0:
            clock = max(clock, int(math.ceil((now.hour * 60 + now.minute) / 15.0)) * 15)
    for i, s in enumerate(sessions):
        obj = S.Session(stage_index=0, stage_label=s["stage_label"], kind=s["kind"], work_id=s["work_id"], minutes=s["minutes"],
                        deep=s["deep"], part=s["part"], parts=s["parts"])
        deep_since_break = deep_since_break + s["minutes"] if s["deep"] else deep_since_break
        raw = S.break_after(obj, deep_since_break, low_load) if i < len(sessions) - 1 else 0
        s["break_after"] = _break_minutes(raw, settings.break_style)
        if s["break_after"] >= 15:
            deep_since_break = 0
        elif s["break_after"] > 0:
            deep_since_break = int(deep_since_break * 0.6)
        if clock is not None:
            s["start_hint"] = _clock(clock)
            clock += s["minutes"] + s["break_after"]
        else:
            s["start_hint"] = None
        s.pop("_stage_obj", None)
        s["text"] = _session_text(s)
    return sessions


def _session_text(s: dict) -> str:
    part = f" (part {s['part']} of {s['parts']})" if s["parts"] > 1 else ""
    brk = f", then a {s['break_after']} minute break" if s["break_after"] else ""
    return f"{s['title']}: {s['stage_label']}{part}, {s['minutes']} minutes{brk}."


def build_schedule(tasks: list, settings: StudySettings, *, now: datetime, energy: Optional[int] = None,
                   stress: Optional[str] = None, studied_today: int = 0, today_minutes: Optional[int] = None,
                   prefs: Optional[dict] = None, alternatives: bool = True) -> dict:
    prefs = prefs or {}
    tasks = [t for t in tasks if t.remaining > 0]
    today = now.date()
    if not tasks:
        return {"days": [], "tasks": {}, "feasibility": {"level": "empty", "feasible": True, "shortfall_minutes": 0, "critical_task": None,
                "load_ratio": 0.0, "fits_at_high": True, "high_shortfall": 0, "buffer_used": False, "needed_extra_per_day": 0,
                "total_minutes": 0, "capacity_minutes": 0}, "alternatives": [], "milestones": [], "gentle": gentle_state(settings, energy, stress),
                "today": today.isoformat(), "notes": ["There is nothing left to schedule."]}
    for t in tasks:
        t.remaining = _ceil5(t.remaining)
    n = _n_days(tasks, now)
    kw = dict(energy=energy, stress=stress, studied_today=studied_today, today_minutes=today_minutes, n_days=n)
    caps = day_capacities(settings, now, n, energy=energy, stress=stress, studied_today=studied_today, today_minutes=today_minutes)
    offs = _offsets(tasks, now, settings.buffer_days, n)

    # ---- which deadlines to plan against: with the safety buffer if that is possible, otherwise the real deadlines
    short_buf, _ = _check(tasks, settings, now, buffer_days=settings.buffer_days, **kw)
    short_real, who_real = _check(tasks, settings, now, buffer_days=0, **kw)
    use_buffer = settings.buffer_days > 0 and short_buf == 0
    last_of = {t.id: offs[t.id]["buffered" if use_buffer else "real"] for t in tasks}
    shortfall = 0 if use_buffer else short_real
    buffer_used = (not use_buffer) and settings.buffer_days > 0 and short_real == 0

    soft_of = {t.id: offs[t.id]["buffered"] for t in tasks}
    plan, left = _allocate(tasks, caps, last_of, settings.pacing, soft_of)

    # ---- sessions per day
    by_id = {t.id: t for t in tasks}
    queues = {t.id: [[dict(s), s["minutes"]] for s in (t.stages or [{"work_id": "general_work", "kind": t.kind, "label": "Work on it", "method":
              "Work on it in focused blocks.", "minutes": t.remaining, "deep": True, "session": [20, 35, 50], "breaks": True}])] for t in tasks}
    for t in tasks:        # make the steps add up to the minutes this plan asks for
        tot = sum(q[1] for q in queues[t.id]) or 1
        if tot != t.remaining:
            f = t.remaining / tot
            for q in queues[t.id]:
                q[1] = max(1, int(round(q[1] * f)))
                q[0]["minutes"] = q[1]
    boundaries = {}
    days_out, first_day, last_day = [], {}, {}
    scheduled = {t.id: 0 for t in tasks}
    for k in range(n):
        d = today + timedelta(days=k)
        alloc = plan.get(k, {})
        sessions = _sessionise(alloc, queues, by_id, k, now, settings, energy=energy, stress=stress, prefs=prefs,
                               boundary_log=boundaries) if alloc else []
        for s in sessions:
            scheduled[s["task_id"]] += s["minutes"]
            first_day.setdefault(s["task_id"], d.isoformat())
            last_day[s["task_id"]] = d.isoformat()
        planned = sum(s["minutes"] for s in sessions)
        days_out.append({"date": d.isoformat(), "label": _label_day(d, today), "weekday": d.weekday(), "capacity": caps[k],
                         "planned": planned, "break_minutes": sum(s["break_after"] for s in sessions), "sessions": sessions})

    # ---- stress test: would it still fit if every task took the high end of its range?
    high_short, _ = _check(tasks, settings, now, buffer_days=0, high=True, **kw)

    total = sum(t.remaining for t in tasks)
    last_needed = max(last_of.values())
    capacity = sum(caps[: last_needed + 1])
    per_task = {}
    pre_win = _prefix(caps)
    for t in tasks:
        L = offs[t.id]["real"]
        real_last_date = (today + timedelta(days=L)).isoformat()
        unsched = left.get(t.id, 0)
        fin = last_day.get(t.id)
        slack = (date.fromisoformat(real_last_date) - date.fromisoformat(fin)).days if fin else None
        # "tight" means little room, not merely "the work is spread out up to the deadline": a 45-minute task in a window with 200 free
        # minutes finishes on its last day under even pacing but is not at risk.
        window = pre_win[min(L + 1, n)]
        share_of_window = t.remaining / max(1, window)
        if unsched > 0:
            status = "late"
        elif slack is not None and slack <= 0 and share_of_window >= 0.5:
            status = "tight"
        else:
            status = "on_track"
        per_task[t.id] = {"title": t.title, "remaining": t.remaining, "scheduled": scheduled[t.id], "unscheduled": unsched,
                          "first_day": first_day.get(t.id), "finish_date": fin, "last_usable_day": real_last_date,
                          "slack_days": slack, "status": status, "flag": offs[t.id]["flag"], "beyond_horizon": offs[t.id]["beyond"]}

    if shortfall > 0:
        level = "infeasible"
    elif buffer_used or high_short > 0 or settings.buffer_days == 0 and any(v["status"] == "tight" for v in per_task.values()):
        level = "tight"
    else:
        level = "comfortable"
    # the task whose deadline breaks first
    critical = who_real if shortfall > 0 else None
    if shortfall > 0 and critical is None:
        late = [tid for tid, v in per_task.items() if v["unscheduled"] > 0]
        critical = late[0] if late else None
    pre_all = _prefix(caps)
    load_ratio = round(total / max(1, pre_all[min(max(offs[t.id]["real"] for t in tasks) + 1, n)]), 2)
    feas = {"level": level, "feasible": shortfall == 0, "shortfall_minutes": int(shortfall),
            "critical_task": ({"id": critical, "title": by_id[critical].title} if critical else None),
            "load_ratio": load_ratio, "fits_at_high": high_short == 0, "high_shortfall": int(high_short),
            "buffer_used": bool(buffer_used), "buffer_days": settings.buffer_days, "needed_extra_per_day": 0,
            "total_minutes": int(total), "capacity_minutes": int(capacity)}

    alts = []
    if alternatives and level in ("infeasible", "tight"):
        late_ids = [tid for tid, v in per_task.items() if v["unscheduled"] > 0]
        alts = find_alternatives(tasks, settings, now, level=level, critical=critical, late_ids=late_ids, **kw)
        if level == "infeasible":
            for a in alts:
                if a["id"] == "more_time":
                    feas["needed_extra_per_day"] = a["effect"]["extra_minutes_per_day"]
    milestones = []
    for tid, bl in boundaries.items():
        t = by_id[tid]
        for j, b in enumerate(bl):
            if j < len(bl) - 1 or len(bl) > 1:
                milestones.append({"task_id": tid, "title": t.title, "label": b["label"], "date": b["date"], "final": j == len(bl) - 1})
    milestones.sort(key=lambda m: (m["date"], m["title"]))

    notes = []
    g = gentle_state(settings, energy, stress)
    if g["on"]:
        why = {"energy": "your energy is low", "wellbeing": "your last wellbeing check was high", "always": "Gentle Mode is always on in Settings"}[g["reason"]]
        notes.append(f"Gentle Mode: daily time is reduced by 20% for the first days because {why}.")
    if any(v["flag"] == "overdue" for v in per_task.values()):
        notes.append("At least one task is already past its deadline, so it is planned as soon as possible.")
    if any(v["beyond_horizon"] for v in per_task.values()):
        notes.append(f"A deadline is more than {MAX_HORIZON} days away; only the next {MAX_HORIZON} days are planned.")
    return {"days": days_out, "tasks": per_task, "feasibility": feas, "alternatives": alts, "milestones": milestones, "gentle": g,
            "today": today.isoformat(), "notes": notes, "pacing": settings.pacing, "use_buffer": use_buffer}


def find_alternatives(tasks: list, settings: StudySettings, now: datetime, *, level: str, critical: Optional[str],
                      late_ids: Optional[list] = None, **kw) -> list:
    """Every alternative returned here was re-checked with the same feasibility test and really removes the shortfall."""
    out = []
    by_id = {t.id: t for t in tasks}

    def ok(**over) -> bool:
        merged = dict(kw)
        merged.update(over)
        s, _ = _check(tasks, settings, now, buffer_days=0 if level == "infeasible" else None, **merged)
        return s == 0

    if level == "infeasible":
        for extra in range(5, 185, 5):
            if ok(extra_per_day=extra):
                out.append({"id": "more_time", "title": "Study a little longer each day",
                            "text": f"About {extra} more minutes on each study day makes everything fit.",
                            "effect": {"extra_minutes_per_day": extra}})
                break
        if len(settings.study_days) < 7 and ok(all_days=True):
            out.append({"id": "rest_days", "title": "Use your rest days",
                        "text": "Everything fits if you also study a little on the days you marked as rest days.", "effect": {"all_days": True}})
        for scope_ids, who in ((([critical] if critical else []), "the task that breaks first"), ([t.id for t in tasks], "all tasks")):
            if not scope_ids:
                continue
            for pct in range(95, 45, -5):
                if ok(scale={tid: pct / 100.0 for tid in scope_ids}):
                    names = by_id[critical].title if who.startswith("the task") else "every task"
                    out.append({"id": "reduce_scope", "title": "Aim for a smaller version",
                                "text": f"Plan for about {pct}% of the work on {names}: the core parts first, extras only if time is left.",
                                "effect": {"scope_percent": pct, "applies_to": "critical" if who.startswith("the task") else "all"}})
                    break
            if any(a["id"] == "reduce_scope" for a in out):
                break
        movers = [tid for tid in (late_ids or []) if tid in by_id] or ([critical] if critical else [])
        if critical and critical not in movers:
            movers.append(critical)
        for extra_days in range(1, 31):
            if movers and ok(extend={tid: extra_days for tid in movers}, n_days=min(MAX_HORIZON, kw["n_days"] + extra_days)):
                dates = {tid: _last_usable_date(by_id[tid].deadline) + timedelta(days=extra_days) for tid in movers}
                names = ", ".join(f"“{by_id[tid].title}” to {dates[tid].strftime('%a %d %b')}" for tid in movers[:3])
                out.append({"id": "extend", "title": "Ask for more time",
                            "text": f"If the deadline could move ({names}), everything would fit. Only your lecturer can agree to that.",
                            "effect": {"task_ids": movers, "extra_days": extra_days, "new_dates": {k: v.isoformat() for k, v in dates.items()}}})
                break
        cands = sorted(tasks, key=lambda t: (t.priority, -(t.deadline.timestamp())))
        freed = []
        for t in cands:
            if ok(drop=(t.id,)):
                freed.append(t)
            if len(freed) == 3:
                break
        if freed:
            t = freed[0]
            out.append({"id": "postpone", "title": "Move one task out of this period",
                        "text": f"If “{t.title}” ({_fmt_hm(t.remaining)}) can wait or be dropped, everything else fits.",
                        "effect": {"task_id": t.id, "minutes_freed": t.remaining, "other_options": [x.title for x in freed[1:]]}})
    else:   # tight: only the cheap, safe suggestions
        for extra in range(5, 65, 5):
            s, _ = _check(tasks, settings, now, high=True, buffer_days=0, extra_per_day=extra, **kw)
            if s == 0:
                out.append({"id": "more_time", "title": "Add a little slack",
                            "text": f"About {extra} more minutes a day would keep the plan safe even if the work takes longer than expected.",
                            "effect": {"extra_minutes_per_day": extra}})
                break
        if settings.pacing != "early":
            out.append({"id": "early", "title": "Start heavier, finish lighter",
                        "text": "Switch pacing to “early” in Settings: more work now leaves more slack near the deadline.",
                        "effect": {"pacing": "early"}})
    return out
