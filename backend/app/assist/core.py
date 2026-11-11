"""
The planning core: pure functions that take plain Python data (loaded from the database for a signed-in student, or sent by the
browser for a guest) and return plans, reports and re-plan proposals. No database, no network, no clock: `now` is an input.
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.taskaware import history as H
from app.taskaware import taxonomy as T

from . import profile as P
from .scheduler import PlanTask, build_schedule, gentle_state
from .settings_schema import StudyProfile, StudySettings

MIN_REMAINING = 15


@dataclass
class TaskRow:
    id: str
    title: str
    deadline: datetime                      # timezone-aware
    status: str = "pending"
    description: str = ""
    category: str = "general"
    difficulty: int = 3
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meta: Optional[dict] = None


@dataclass
class CoreInput:
    now: datetime
    settings: StudySettings
    tasks: list
    profile: StudyProfile = field(default_factory=StudyProfile)
    energy: Optional[int] = None
    stress: Optional[str] = None
    skills: dict = field(default_factory=dict)
    outcomes: list = field(default_factory=list)
    sessions: list = field(default_factory=list)           # [H.SessionRecord]
    studied_today: int = 0
    length_bias: dict = field(default_factory=dict)         # kind -> 0.85 / 1.0 / 1.15 from the student's "too long / too short" answers
    today_minutes: Optional[int] = None                     # "how much time do you have today?" from today's check-in


def apply_mood(core: "CoreInput") -> "CoreInput":
    """Today's optional check-in feeds the plan: high self-reported stress lightens it (like a high wellbeing check), and the minutes
    the student has today replace the usual daily time for today only. Yesterday's check-in never carries over."""
    today = core.now.date().isoformat()
    entry = next((e for e in reversed(core.profile.mood_log) if e.get("date") == today), None)
    if entry:
        if entry.get("stress") == "high":
            core.stress = "High"
        if entry.get("today_minutes") is not None:
            core.today_minutes = int(entry["today_minutes"])
    return core


def tz_of(settings: StudySettings) -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def make_deadline(d: date, hour: Optional[int], tz: ZoneInfo) -> datetime:
    if hour is None:
        return datetime(d.year, d.month, d.day, 23, 59, tzinfo=tz)
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=tz)


# ---------------------------------------------------------------- meta
def remaining_of(meta: dict) -> tuple:
    likely, high, done = int(meta["likely"]), int(meta["high"]), int(meta.get("done", 0))
    rem = likely - done
    if rem < MIN_REMAINING:
        rem = max(MIN_REMAINING, int(likely * 0.15)) if done >= likely else max(MIN_REMAINING, rem)
    rem = int(-(-rem // 5) * 5)
    rem_high = max(rem, int(-(-(high - done) // 5) * 5))
    return rem, rem_high


def meta_from_profile(prof: dict, *, source: str = "rules", priority: int = 2) -> dict:
    keep = {k: prof[k] for k in ("kind", "kind_label", "intrinsic", "personal", "low", "likely", "high", "stages", "confidence", "uncertainty",
                                 "difficulty_label", "difficulty_text", "workload_text", "understanding", "uncertainties", "basis", "size",
                                 "skill_kind", "history", "raw_likely") if k in prof}
    keep.update({"done": 0, "source": source, "priority": priority})
    if prof.get("second_opinion"):
        keep["second_opinion"] = prof["second_opinion"]
    return keep


def ensure_meta(row: TaskRow, core: CoreInput) -> dict:
    if row.meta and row.meta.get("stages") and row.meta.get("likely"):
        return row.meta
    prof = P.public(P.profile_task(row.title, row.description, self_difficulty=row.difficulty if row.difficulty in (1, 2, 3, 4, 5) else None,
                                   skills=core.skills, outcomes=core.outcomes, sessions=core.sessions))
    meta = meta_from_profile(prof)
    if row.meta:
        meta["done"] = int(row.meta.get("done", 0))
        meta["priority"] = int(row.meta.get("priority", 2))
    return meta


def to_plan_task(row: TaskRow, meta: dict) -> PlanTask:
    rem, rem_high = remaining_of(meta)
    return PlanTask(id=row.id, title=row.title, deadline=row.deadline.astimezone(row.deadline.tzinfo), remaining=rem, remaining_high=rem_high,
                    kind=meta["kind"], difficulty=float(meta["personal"]),
                    stages=P.stages_after(meta["stages"], int(meta.get("done", 0)), rem), priority=int(meta.get("priority", 2)),
                    est_likely=int(meta["likely"]))


def _prefs_for(core: CoreInput, metas: list) -> dict:
    prefs = {}
    for m in metas:
        k = m["kind"]
        if k in prefs:
            continue
        base = max((s["session"][1] for s in m["stages"] if s["kind"] == k), default=40)
        p = H.preferred_session(k, core.sessions, base)
        if p:
            prefs[k] = p
    if core.length_bias:
        prefs["_bias"] = dict(core.length_bias)
    return prefs


def apply_remaining(meta: dict, remaining: int) -> dict:
    """The student says how much is left. Their word beats the estimate: likely becomes done + remaining and the range follows."""
    done = int(meta.get("done", 0))
    likely = done + max(0, int(remaining))
    meta["likely"] = max(likely, 1)
    meta["low"] = min(int(meta["low"]), meta["likely"])
    meta["high"] = max(int(meta["high"]), int(meta["likely"] * 1.2))
    return meta


def length_bias_from(rows: list) -> dict:
    """rows: [(kind, length_feel)] newest first. Three or more answers for a kind with a clear majority nudge block length by 15%."""
    out = {}
    per = {}
    for kind, feel in rows:
        if feel in ("short", "long", "right"):
            per.setdefault(kind, [])
            if len(per[kind]) < 6:
                per[kind].append(feel)
    for kind, feels in per.items():
        if len(feels) < 3:
            continue
        diff = feels.count("long") - feels.count("short")
        if diff >= 2:
            out[kind] = 0.85
        elif diff <= -2:
            out[kind] = 1.15
    return out


# ---------------------------------------------------------------- drafts
@dataclass
class Draft:
    ref: str
    title: str
    deadline_date: Optional[date] = None
    deadline_hour: Optional[int] = None
    details: str = ""
    kind: Optional[str] = None
    felt_hard: Optional[int] = None
    answers: dict = field(default_factory=dict)
    ai_estimate: Optional[dict] = None
    subtasks: list = field(default_factory=list)
    priority: int = 2


def draft_to_row(d: Draft, core: CoreInput) -> tuple:
    tz = tz_of(core.settings)
    prof = P.profile_task(d.title, d.details, self_difficulty=d.felt_hard, skills=core.skills, outcomes=core.outcomes,
                          sessions=core.sessions, answers=d.answers, kind_override=d.kind)
    source = "rules"
    if d.ai_estimate:
        P.widen_with_second_opinion(prof, d.ai_estimate.get("low"), d.ai_estimate.get("likely"), d.ai_estimate.get("high"))
        source = "blended"
    if d.subtasks:
        P.apply_subtasks(prof, d.subtasks)
        source = "ai" if source == "rules" else source
    prof = P.public(prof)
    meta = meta_from_profile(prof, source=source, priority=d.priority)
    done_pct = d.answers.get("progress")
    row = TaskRow(id=f"draft:{d.ref}", title=d.title, deadline=make_deadline(d.deadline_date, d.deadline_hour, tz),
                  description=d.details, difficulty=max(1, min(5, int(round(meta["personal"])))), category=meta["kind_label"], meta=meta,
                  created_at=core.now)
    return row, meta


# ---------------------------------------------------------------- scheduling views
def plan_for(core: CoreInput, drafts: Optional[list] = None, *, alternatives: bool = True, today_minutes: Optional[int] = None) -> dict:
    rows, metas = [], {}
    for r in core.tasks:
        if r.status != "pending":
            continue
        m = ensure_meta(r, core)
        rows.append(r)
        metas[r.id] = m
    for d in drafts or []:
        row, m = draft_to_row(d, core)
        rows.append(row)
        metas[row.id] = m
    plan_tasks = [to_plan_task(r, metas[r.id]) for r in rows]
    prefs = _prefs_for(core, list(metas.values()))
    if today_minutes is None:
        today_minutes = core.today_minutes
    res = build_schedule(plan_tasks, core.settings, now=core.now, energy=core.energy, stress=core.stress, studied_today=core.studied_today,
                         today_minutes=today_minutes, prefs=prefs, alternatives=alternatives)
    res["_rows"] = {r.id: r for r in rows}
    res["_metas"] = metas
    res["_plan_tasks"] = {t.id: t for t in plan_tasks}
    return res


SETTINGS_KEYS_THAT_CHANGE_A_PLAN = ("weekday_minutes", "weekend_minutes", "study_days", "buffer_days", "pacing", "preferred_time",
                                    "session_style", "break_style", "gentle_mode", "timezone")


def settings_fingerprint(s: StudySettings) -> str:
    d = s.model_dump()
    keyed = {k: d[k] for k in SETTINGS_KEYS_THAT_CHANGE_A_PLAN}
    for k in ("day_minutes", "unavailable_periods"):      # added later: left out while unused so plans stored earlier keep their fingerprint
        if d[k]:
            keyed[k] = d[k]
    return hashlib.sha1(json.dumps(keyed, sort_keys=True).encode()).hexdigest()[:12]


def snapshot(core: CoreInput, res: dict) -> dict:
    return {"day": core.now.date().isoformat(), "settings": settings_fingerprint(core.settings),
            "stress": core.stress, "energy_low": bool(core.energy is not None and core.energy <= 2),
            "tasks": {tid: {"deadline": res["_rows"][tid].deadline.isoformat(), "remaining": res["_plan_tasks"][tid].remaining}
                      for tid in res["tasks"]}}


def plan_facts(core: CoreInput, res: dict) -> dict:
    """The compact, number-bearing summary that is given to the language model (and used by the local wording)."""
    f = res["feasibility"]
    if f["level"] == "empty":
        return {"level": "empty"}
    today_sessions = []
    first_any = None
    for d in res["days"]:
        for s in d["sessions"]:
            item = {"title": s["title"], "stage": s["stage_label"], "minutes": s["minutes"], "method": s["method"], "start_hint": s.get("start_hint")}
            if first_any is None:
                first_any = dict(item, date=d["date"])
            if d["date"] == res["today"]:
                today_sessions.append(item)
    tasks = []
    for tid, v in res["tasks"].items():
        m = res["_metas"][tid]
        row = res["_rows"][tid]
        tasks.append({"title": v["title"], "deadline": row.deadline.date().isoformat(), "remaining_minutes": v["remaining"], "status": v["status"],
                      "finish_date": v["finish_date"], "difficulty_for_you": float(m["personal"]), "range_minutes": [m["low"], m["high"]]})
    brk = next((s["break_after"] for d in res["days"] for s in d["sessions"] if s["break_after"]), 0)
    return {"level": f["level"], "feasible": f["feasible"], "shortfall_minutes": f["shortfall_minutes"], "total_minutes": f["total_minutes"],
            "capacity_minutes": f["capacity_minutes"], "fits_at_high": f["fits_at_high"], "high_shortfall": f["high_shortfall"],
            "buffer_used": f["buffer_used"], "energy": core.energy, "gentle_mode": res["gentle"]["on"], "today": today_sessions,
            "first_session": first_any, "tasks": tasks[:8],
            "alternatives": [{"id": a["id"], "text": a["text"]} for a in res["alternatives"][:3]],
            "break_note": (f"Take the {brk} minute breaks away from screens." if brk else None), "today_date": res["today"]}


def public_result(res: dict) -> dict:
    return {k: v for k, v in res.items() if not k.startswith("_")}


# ---------------------------------------------------------------- re-plan detection
def replan_check(core: CoreInput, active: Optional[dict], past_sessions: list) -> dict:
    """
    active: {"inputs": snapshot, "summary": {...}} of the stored plan, or None.
    past_sessions: [{"day": iso, "task_id", "minutes", "status"}] the plan had on days before today.
    Returns {"needed": bool, "reasons": [{"code","text"}], "proposal": plan or None, "changes": [...]}.
    """
    pending = [r for r in core.tasks if r.status == "pending"]
    if active is None:
        return {"needed": False, "reasons": [], "proposal": None, "changes": [], "has_plan": False,
                "unplanned": len(pending)}
    snap = active["inputs"]
    reasons = []
    now_ids = {r.id: r for r in pending}
    for tid, v in snap["tasks"].items():
        r = now_ids.get(tid)
        if r is not None and r.deadline != datetime.fromisoformat(v["deadline"]):
            reasons.append({"code": "deadline", "text": f"The deadline of “{r.title}” changed."})
            break
    new_tasks = [r for tid, r in now_ids.items() if tid not in snap["tasks"]]
    gone = [tid for tid in snap["tasks"] if tid not in now_ids and not any(t.id == tid and t.status == "completed" for t in core.tasks)]
    if new_tasks:
        reasons.append({"code": "tasks", "text": f"{len(new_tasks)} new task{'s' if len(new_tasks) != 1 else ''} {'are' if len(new_tasks) != 1 else 'is'} not in your plan yet."})
    elif gone:
        reasons.append({"code": "tasks", "text": "A task in your plan was removed."})
    if settings_fingerprint(core.settings) != snap.get("settings"):
        reasons.append({"code": "settings", "text": "You changed your study settings after this plan was made."})
    low_now = bool(core.energy is not None and core.energy <= 2)
    if low_now and not snap.get("energy_low"):
        reasons.append({"code": "energy", "text": "Your energy is low today, so today's plan may be too heavy."})
    if core.stress == "High" and snap.get("stress") != "High":
        reasons.append({"code": "wellbeing", "text": "Your latest wellbeing check was high, so a lighter plan is suggested."})
    today = core.now.date().isoformat()
    missed = sum(s["minutes"] for s in past_sessions if s["day"] < today and s["status"] == "planned")
    behind = 0
    for tid, v in snap["tasks"].items():
        r = now_ids.get(tid)
        if r is None:
            continue
        m = ensure_meta(r, core)
        rem_now, _ = remaining_of(m)
        planned_before = sum(s["minutes"] for s in past_sessions if s["task_id"] == tid and s["day"] < today)
        expected = max(0, v["remaining"] - planned_before)
        behind += max(0, rem_now - expected)
    if missed >= 15 or behind >= 15:
        reasons.append({"code": "behind", "text": f"You are about {_hm(max(missed, behind))} behind the plan. A catch-up plan can spread it out."})
    if not reasons:
        return {"needed": False, "reasons": [], "proposal": None, "changes": [], "has_plan": True, "unplanned": 0}
    res = plan_for(core, alternatives=True)
    changes = diff_plans(active.get("future", []), res, today)
    return {"needed": True, "reasons": reasons, "proposal": res, "changes": changes, "has_plan": True, "unplanned": len(new_tasks)}


def _hm(m: int) -> str:
    h, mm = divmod(int(m), 60)
    return f"{h} h {mm} min" if h and mm else f"{h} h" if h else f"{mm} min"


def diff_plans(old_future: list, new_res: dict, today: str) -> list:
    """Plain-English list of what would change: minutes per day and per task."""
    old_day, new_day = {}, {}
    for s in old_future:
        old_day[s["day"]] = old_day.get(s["day"], 0) + s["minutes"]
    for d in new_res["days"]:
        new_day[d["date"]] = d["planned"]
    out = []
    for day in sorted(set(old_day) | set(new_day))[:7]:
        a, b = old_day.get(day, 0), new_day.get(day, 0)
        if abs(a - b) >= 10:
            out.append({"date": day, "before": a, "after": b})
    return out


# ---------------------------------------------------------------- explanation of the plan, step by step ("Explain my plan")
def explain_steps(core: CoreInput, res: dict) -> list:
    """Deterministic, always-available reasons behind the plan. The language model may re-word them but never replaces them."""
    out = []
    f = res["feasibility"]
    s = core.settings
    out.append(f"I used {_hm(s.weekday_minutes)} on weekdays and {_hm(s.weekend_minutes)} at weekends, on {len(s.study_days)} study day{'s' if len(s.study_days) != 1 else ''} a week (your Settings).")
    if res["gentle"]["on"]:
        out.append("Gentle Mode is on, so the first days are about 20% lighter and easy work comes first when your energy is low.")
    out.append(f"Work is placed in order of deadline: the task due first gets time first. Pacing is “{s.pacing}”: "
               + ("work is spread evenly so no day is crammed." if s.pacing == "even" else "work starts early so the last days stay free."))
    if s.buffer_days:
        out.append(f"I tried to finish {s.buffer_days} day{'s' if s.buffer_days != 1 else ''} before each deadline" + (" and managed to." if res.get("use_buffer") else ", but that did not fit, so the buffer was used."))
    if f["level"] in ("tight", "infeasible"):
        out.append("I also tested the plan against the high end of each estimate: " + ("it still fits." if f["fits_at_high"] else f"it would be about {_hm(f['high_shortfall'])} short."))
    return out
