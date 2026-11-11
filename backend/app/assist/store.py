"""Database side of the planner: load everything into the pure core's input, and save plans, metas and sessions."""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (EnergyCheckin, SessionLog, Task, TaskOutcome, TaskStatus, User, UserSkill, WellbeingCheck)
from app.taskaware import history as H
from app.wellbeing import latest_recent_label

from . import core as C
from .models import PlanSession, StudyPlan, TaskMeta, TaskSession, UserProfile, UserSettings
from .settings_schema import StudyProfile, StudySettings, profile_from, settings_from

ENERGY_FRESH_HOURS = 24
META_COLUMNS = ("kind", "intrinsic", "personal", "low", "likely", "high", "done", "stages", "source", "priority")


def meta_to_dict(m: TaskMeta) -> dict:
    d = dict(m.extra or {})
    d.update({"kind": m.kind, "intrinsic": m.intrinsic_difficulty, "personal": m.personal_difficulty, "low": m.est_low, "likely": m.est_likely,
              "high": m.est_high, "done": m.done_minutes, "stages": m.stages or [], "source": m.source, "priority": m.priority})
    return d


async def save_meta(db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID, meta: dict) -> None:
    extra = {k: v for k, v in meta.items() if k not in META_COLUMNS}
    row = await db.get(TaskMeta, task_id)
    vals = dict(kind=meta["kind"], intrinsic_difficulty=float(meta["intrinsic"]), personal_difficulty=float(meta["personal"]), est_low=int(meta["low"]),
                est_likely=int(meta["likely"]), est_high=int(meta["high"]), done_minutes=int(meta.get("done", 0)), stages=meta["stages"],
                source=meta.get("source", "rules"), priority=int(meta.get("priority", 2)), extra=extra)
    if row is None:
        db.add(TaskMeta(task_id=task_id, user_id=user_id, **vals))
    else:
        for k, v in vals.items():
            setattr(row, k, v)


async def get_settings(db: AsyncSession, user_id: uuid.UUID) -> StudySettings:
    row = await db.get(UserSettings, user_id)
    return settings_from(row.data if row else None)


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> StudyProfile:
    row = await db.get(UserProfile, user_id)
    return profile_from(row.data if row else None)


async def load_core(db: AsyncSession, user: User, *, settings: Optional[StudySettings] = None) -> C.CoreInput:
    settings = settings or await get_settings(db, user.id)
    tz = C.tz_of(settings)
    now = datetime.now(timezone.utc).astimezone(tz)
    tasks = (await db.scalars(select(Task).where(Task.owner_id == user.id).order_by(Task.deadline))).all()
    metas = {m.task_id: meta_to_dict(m) for m in (await db.scalars(select(TaskMeta).where(TaskMeta.user_id == user.id))).all()}
    rows = [C.TaskRow(id=str(t.id), title=t.title, deadline=t.deadline.astimezone(tz) if t.deadline.tzinfo else t.deadline.replace(tzinfo=timezone.utc).astimezone(tz),
                      status=t.status.value, description=t.description, category=t.category, difficulty=t.difficulty, created_at=t.created_at,
                      completed_at=t.completed_at, meta=metas.get(t.id)) for t in tasks]
    last = await db.scalar(select(EnergyCheckin).where(EnergyCheckin.user_id == user.id).order_by(EnergyCheckin.created_at.desc()).limit(1))
    energy = None
    if last is not None:
        ts = last.created_at if last.created_at.tzinfo else last.created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - ts <= timedelta(hours=ENERGY_FRESH_HOURS):
            energy = last.energy_level
    stress = await latest_recent_label(db, user.id)
    skills = {s.kind: s.level for s in (await db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))).all()}
    outs = (await db.scalars(select(TaskOutcome).where(TaskOutcome.user_id == user.id).order_by(TaskOutcome.created_at.desc()).limit(200))).all()
    sess = (await db.scalars(select(SessionLog).where(SessionLog.user_id == user.id).order_by(SessionLog.created_at.desc()).limit(300))).all()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    today_rows = (await db.scalars(select(TaskSession).where(TaskSession.user_id == user.id, TaskSession.created_at >= day_start))).all()
    core = C.CoreInput(now=now, settings=settings, tasks=rows, profile=await get_profile(db, user.id), energy=energy, stress=stress, skills=skills,
                       outcomes=[H.Outcome(o.kind, o.raw_minutes, o.actual_minutes, o.felt, o.predicted_personal) for o in outs],
                       sessions=[H.SessionRecord(s.kind, s.minutes, s.completed, s.focus) for s in sess],
                       studied_today=sum(s.actual_minutes for s in today_rows))
    return C.apply_mood(core)


async def persist_missing_meta(db: AsyncSession, user: User, core: C.CoreInput) -> None:
    """Give every pending task stored planning facts the first time they are needed, so they stay stable between visits."""
    changed = False
    for r in core.tasks:
        if r.status != "pending" or (r.meta and r.meta.get("stages") and r.meta.get("likely")):
            continue
        r.meta = C.ensure_meta(r, core)
        await save_meta(db, user.id, uuid.UUID(r.id), r.meta)
        changed = True
    if changed:
        await db.commit()


# ---------------------------------------------------------------- plans
def compact_summary(res: dict, core: C.CoreInput) -> dict:
    pub = C.public_result(res)
    return {"feasibility": pub["feasibility"], "tasks": pub["tasks"], "alternatives": pub["alternatives"], "milestones": pub["milestones"],
            "notes": pub["notes"], "gentle": pub["gentle"], "pacing": pub.get("pacing"), "use_buffer": pub.get("use_buffer"),
            "capacities": {d["date"]: d["capacity"] for d in pub["days"]}, "today": pub["today"],
            "explain": C.explain_steps(core, res)}


async def active_plan(db: AsyncSession, user_id: uuid.UUID) -> Optional[StudyPlan]:
    return await db.scalar(select(StudyPlan).where(StudyPlan.user_id == user_id, StudyPlan.status == "active").order_by(StudyPlan.created_at.desc()).limit(1))


async def store_plan(db: AsyncSession, user: User, core: C.CoreInput, res: dict, reason: str) -> StudyPlan:
    """Save a new active plan. History is never thrown away:
      - blocks that were done, partly done, skipped or marked not-done stay where they are (they belong to the student's record);
      - old blocks from earlier days that were never confirmed become "missed" (the new plan carries the unfinished work forward);
      - only FUTURE blocks that are still just "planned" or "delayed" are replaced by the new plan;
      - blocks the student added by hand (no task) are carried over to the new plan, so a replan never silently deletes them."""
    today = core.now.date()
    old = await active_plan(db, user.id)
    plan = StudyPlan(user_id=user.id, status="active", reason=reason, summary=compact_summary(res, core), inputs=C.snapshot(core, res))
    if old is not None:
        old.status = "superseded"
        await db.execute(delete(PlanSession).where(PlanSession.plan_id == old.id, PlanSession.day >= today, PlanSession.status.in_(("planned", "delayed")),
                                                   PlanSession.task_id.is_not(None)))
        await db.execute(update(PlanSession).where(PlanSession.plan_id == old.id, PlanSession.day < today, PlanSession.status == "planned").values(status="missed"))
    db.add(plan)
    await db.flush()
    if old is not None:
        # the student's own blocks (no task behind them) move into the new plan as they are
        await db.execute(update(PlanSession).where(PlanSession.plan_id == old.id, PlanSession.task_id.is_(None), PlanSession.day >= today,
                                                   PlanSession.status.in_(("planned", "delayed"))).values(plan_id=plan.id))
    for d in res["days"]:
        for i, s in enumerate(d["sessions"]):
            db.add(PlanSession(plan_id=plan.id, user_id=user.id, task_id=uuid.UUID(s["task_id"]), day=date.fromisoformat(d["date"]), position=i,
                               minutes=s["minutes"], break_after=s["break_after"], label=s["stage_label"][:200], method=s["method"][:400],
                               start_hint=s.get("start_hint"), status="planned"))
    await db.commit()
    return plan


async def plan_view(db: AsyncSession, user_id: uuid.UUID, tasks_by_id: dict, today: date) -> Optional[dict]:
    plan = await active_plan(db, user_id)
    if plan is None:
        return None
    rows = (await db.scalars(select(PlanSession).where(PlanSession.plan_id == plan.id).order_by(PlanSession.day, PlanSession.position))).all()
    caps = plan.summary.get("capacities", {})
    by_day = {}
    for s in rows:
        t = tasks_by_id.get(str(s.task_id))
        by_day.setdefault(s.day.isoformat(), []).append({
            "id": str(s.id), "task_id": str(s.task_id) if s.task_id else None, "title": t.title if t else "(removed task)", "stage_label": s.label,
            "method": s.method, "minutes": s.minutes, "break_after": s.break_after, "start_hint": s.start_hint, "status": s.status,
            "text": f"{t.title if t else 'Task'}: {s.label}, {s.minutes} minutes" + (f", then a {s.break_after} minute break" if s.break_after else "") + "."})
    days = []
    for iso in sorted(set(caps) | set(by_day)):
        d = date.fromisoformat(iso)
        sessions = by_day.get(iso, [])
        delta = (d - today).days
        days.append({"date": iso, "label": "Today" if delta == 0 else "Tomorrow" if delta == 1 else d.strftime("%a %d %b"), "weekday": d.weekday(),
                     "capacity": caps.get(iso, 0), "planned": sum(x["minutes"] for x in sessions if x["status"] != "skipped"), "sessions": sessions})
    return {"id": str(plan.id), "created_at": plan.created_at.isoformat(), "reason": plan.reason, "days": days, **{k: plan.summary.get(k) for k in
            ("feasibility", "tasks", "alternatives", "milestones", "notes", "gentle", "pacing", "explain")}, "inputs": plan.inputs}


async def plan_sessions_for_check(db: AsyncSession, user_id: uuid.UUID, today: date) -> tuple:
    """(past sessions, future sessions) of the ACTIVE plan, as the pure replan check wants them."""
    plan = await active_plan(db, user_id)
    if plan is None:
        return [], []
    rows = (await db.scalars(select(PlanSession).where(PlanSession.plan_id == plan.id))).all()
    f = lambda s: {"day": s.day.isoformat(), "task_id": str(s.task_id) if s.task_id else None, "minutes": s.minutes, "status": s.status}
    return [f(s) for s in rows if s.day < today], [f(s) for s in rows if s.day >= today]
