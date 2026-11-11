"""
My Tasks: the whole saved roadmap, and everything a student can do with it.

  GET    /roadmap                      the full roadmap and progress (today, tomorrow, all days, completed, overdue, deadlines)
  POST   /roadmap/items                add a study block of your own
  PATCH  /roadmap/items/{id}           edit title, subject, minutes, day, label or note
  DELETE /roadmap/items/{id}?confirm=true   remove a block (never a confirmed one)
  POST   /roadmap/items/{id}/confirm   Done / Partly done / Not done / Delayed (+ minutes studied and how it went)
  POST   /roadmap/items/{id}/undo      take a confirmation back
  POST   /roadmap/items/{id}/move      move to another day (postpone)
  POST   /roadmap/replan/preview       what a new plan would change - nothing is saved
  POST   /roadmap/replan/apply         save the new plan (needs confirm: true); history is kept
  GET    /roadmap/history              what happened, newest first

Nothing here uses a language model. Every change is checked against the signed-in student's own rows and written to plan_events,
so the history can always explain how the roadmap became what it is.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.sanitize import clean_text
from app.auth import get_current_user
from app.database import get_db
from app.models import SessionLog, Task, TaskOutcome, TaskStatus, User

from . import core as C
from . import reminders as RM
from . import roadmap_view as RV
from . import store
from .models import PlanEvent, PlanSession, StudyPlan, TaskMeta, TaskSession
from .requests import SessionFeedbackIn
from .routes import log_session

router = APIRouter(prefix="/roadmap", tags=["my tasks (roadmap)"])

MAX_HORIZON_DAYS = 400


# ---------------------------------------------------------------- requests
class ConfirmIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["done", "partial", "not_done", "delayed"]
    actual_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    felt: Optional[Literal["easy", "okay", "difficult"]] = None
    remaining_minutes: Optional[int] = Field(default=None, ge=0, le=6000)
    new_day: Optional[date] = None
    note: str = Field(default="", max_length=200)

    @field_validator("note")
    @classmethod
    def _n(cls, v: str) -> str:
        return clean_text(v, 200)


class MoveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day: date


class EditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=100)
    label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    method: Optional[str] = Field(default=None, max_length=400)
    minutes: Optional[int] = Field(default=None, ge=5, le=600)
    day: Optional[date] = None

    @field_validator("title", "subject", "label", "method")
    @classmethod
    def _c(cls, v):
        return clean_text(v, 400) if v is not None else v


class AddIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    subject: str = Field(default="My other tasks", min_length=1, max_length=100)
    minutes: int = Field(ge=5, le=600)
    day: date
    label: str = Field(default="My own study block", max_length=200)
    method: str = Field(default="", max_length=400)
    task_id: Optional[uuid.UUID] = None

    @field_validator("title", "subject", "label", "method")
    @classmethod
    def _c(cls, v):
        return clean_text(v, 400)


class ReplanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: bool = False
    reason: Literal["energy", "deadline", "settings", "behind", "tasks", "wellbeing", "manual"] = "manual"


# ---------------------------------------------------------------- helpers
def block_dict(s: PlanSession) -> dict:
    return {"id": str(s.id), "task_id": str(s.task_id) if s.task_id else None, "day": s.day.isoformat(), "position": s.position, "minutes": s.minutes,
            "actual_minutes": s.actual_minutes or 0, "break_after": s.break_after, "label": s.label, "method": s.method, "start_hint": s.start_hint,
            "status": s.status, "title": s.title, "subject": s.subject, "manual": bool(s.manual), "original_day": s.original_day.isoformat() if s.original_day else None,
            "felt": s.felt, "completed_at": s.completed_at.isoformat() if s.completed_at else None}


def task_dicts(core: C.CoreInput) -> list:
    tz = C.tz_of(core.settings)
    return [{"id": r.id, "title": r.title, "subject": (r.meta or {}).get("subject"), "status": r.status, "difficulty": r.difficulty,
             "deadline": r.deadline.astimezone(tz).date().isoformat()} for r in core.tasks]


async def roadmap_blocks(db: AsyncSession, user_id: uuid.UUID) -> list:
    rows = (await db.scalars(select(PlanSession).where(PlanSession.user_id == user_id).order_by(PlanSession.day, PlanSession.position))).all()
    return [block_dict(s) for s in rows]


async def full_view(db: AsyncSession, user: User, core: Optional[C.CoreInput] = None) -> dict:
    core = core or await store.load_core(db, user)
    view = RV.build_view(await roadmap_blocks(db, user.id), task_dicts(core), core.now.date())
    view["time_zone"] = core.settings.timezone
    view["reminders"] = RM.summary_for(view, core.now.date())
    return view


async def _own_block(db: AsyncSession, user: User, item_id: str) -> PlanSession:
    try:
        ps = await db.get(PlanSession, uuid.UUID(item_id))
    except ValueError:
        ps = None
    if ps is None or ps.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Study block not found")
    return ps


def _event(db: AsyncSession, user: User, ps_id, kind: str, detail: dict) -> None:
    db.add(PlanEvent(user_id=user.id, plan_session_id=ps_id, kind=kind, detail=detail))


def _check_day(d: date, today: date) -> None:
    if d < today:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose today or a later day.")
    if d > today + timedelta(days=MAX_HORIZON_DAYS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That day is too far away.")


async def _unfinished_elsewhere(db: AsyncSession, ps: PlanSession) -> int:
    rows = (await db.scalars(select(PlanSession).where(PlanSession.user_id == ps.user_id, PlanSession.task_id == ps.task_id,
                                                       PlanSession.id != ps.id))).all()
    return sum(1 for r in rows if r.status in ("planned", "delayed", "not_done", "missed", "partial"))


async def _revert_confirmation(db: AsyncSession, user: User, ps: PlanSession) -> None:
    """Take a "done" / "partly done" back: the minutes leave the task's progress and the learning record, the block is planned again."""
    sessions = (await db.scalars(select(TaskSession).where(TaskSession.plan_session_id == ps.id, TaskSession.user_id == user.id))).all()
    studied = sum(t.actual_minutes for t in sessions) or ps.actual_minutes
    for t in sessions:
        kind = t.kind
        log = await db.scalar(select(SessionLog).where(SessionLog.user_id == user.id, SessionLog.kind == kind, SessionLog.minutes == max(5, t.actual_minutes))
                              .order_by(SessionLog.created_at.desc()).limit(1))
        if log is not None:
            await db.delete(log)
        await db.delete(t)
    if ps.task_id:
        row = await db.scalar(select(TaskMeta).where(TaskMeta.task_id == ps.task_id, TaskMeta.user_id == user.id))
        if row is not None:
            meta = store.meta_to_dict(row)
            meta["done"] = max(0, int(meta.get("done", 0)) - studied)
            await store.save_meta(db, user.id, ps.task_id, meta)
        task = await db.get(Task, ps.task_id)
        if task is not None and task.owner_id == user.id and task.status == TaskStatus.completed:
            task.status, task.completed_at = TaskStatus.pending, None
            out = await db.scalar(select(TaskOutcome).where(TaskOutcome.user_id == user.id).order_by(TaskOutcome.created_at.desc()).limit(1))
            if out is not None:
                await db.delete(out)
    ps.status, ps.actual_minutes, ps.completed_at, ps.felt = "planned", 0, None, None


# ---------------------------------------------------------------- reading
@router.get("")
async def get_roadmap(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    view = await full_view(db, user, core)
    plan = await store.active_plan(db, user.id)
    view["plan"] = {"id": str(plan.id), "created_at": plan.created_at.isoformat(), "reason": plan.reason} if plan else None
    return view


@router.get("/history")
async def history(limit: int = Query(default=60, ge=1, le=200), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.scalars(select(PlanEvent).where(PlanEvent.user_id == user.id).order_by(PlanEvent.created_at.desc()).limit(limit))).all()
    return {"events": [{"id": str(e.id), "kind": e.kind, "detail": e.detail, "created_at": e.created_at.isoformat(), "block_id": str(e.plan_session_id) if e.plan_session_id else None}
                       for e in rows]}


# ---------------------------------------------------------------- confirming progress
@router.post("/items/{item_id}/confirm")
async def confirm(item_id: str, body: ConfirmIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    ps = await _own_block(db, user, item_id)
    core = await store.load_core(db, user)
    today = core.now.date()
    if ps.status in ("done", "partial"):
        await _revert_confirmation(db, user, ps)            # changing your answer replaces the old one, it never adds to it
    before = ps.status
    learned, replan_hint, task_completed = [], False, False
    if body.status in ("done", "partial"):
        actual = body.actual_minutes or ps.minutes
        if body.status == "partial" and actual >= ps.minutes and body.actual_minutes:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Partly done means you studied less than planned. Choose Done instead.")
        task_done = False
        if body.status == "done" and ps.task_id and await _unfinished_elsewhere(db, ps) == 0:
            row = next((r for r in core.tasks if r.id == str(ps.task_id)), None)
            if row is not None and row.status == "pending":
                rem = C.remaining_of(C.ensure_meta(row, core))[0]
                task_done = (rem - actual) <= 20 or body.remaining_minutes == 0
        await db.commit()                                    # log_session commits too; keep this step's undo/clear first
        res = await log_session(SessionFeedbackIn(plan_session_id=str(ps.id), status=body.status, planned_minutes=ps.minutes, actual_minutes=actual,
                                                  felt=body.felt, task_done=task_done, remaining_minutes=body.remaining_minutes), user, db)
        learned, replan_hint, task_completed = res["learned"], res["replan_suggested"], res.get("task_completed", False)
        ps = await _own_block(db, user, item_id)
        if body.status == "partial":
            replan_hint = True
            learned.append(f"Saved {actual} of {ps.minutes} minutes. The rest stays on your list and a new plan can place it.")
        _event(db, user, ps.id, "confirmed", {"status": body.status, "minutes": actual, "planned": ps.minutes, "felt": body.felt, "title": ps.title or ps.label, "before": before})
    elif body.status == "not_done":
        ps.status, ps.actual_minutes, ps.completed_at = "not_done", 0, None
        replan_hint = True
        learned.append("Noted. Nothing is lost: the work stays on your list and a new plan can place it on another day.")
        _event(db, user, ps.id, "confirmed", {"status": "not_done", "planned": ps.minutes, "note": body.note, "title": ps.title or ps.label, "before": before})
    else:   # delayed
        new_day = body.new_day or (today + timedelta(days=1))
        _check_day(new_day, today)
        ps.original_day = ps.original_day or ps.day
        _event(db, user, ps.id, "confirmed", {"status": "delayed", "from": ps.day.isoformat(), "to": new_day.isoformat(), "title": ps.title or ps.label, "before": before})
        ps.day, ps.status = new_day, "delayed"
        learned.append(f"Moved to {RV.day_label(new_day, today)}.")
    await db.commit()
    return {"saved": True, "learned": learned, "replan_suggested": replan_hint, "task_completed": task_completed, "view": await full_view(db, user)}


@router.post("/items/{item_id}/undo")
async def undo(item_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    ps = await _own_block(db, user, item_id)
    if ps.status == "planned":
        raise HTTPException(status.HTTP_409_CONFLICT, "Nothing to undo for this block.")
    was = ps.status
    if ps.status in ("done", "partial"):
        await _revert_confirmation(db, user, ps)
    else:
        if ps.status == "delayed" and ps.original_day:
            ps.day = ps.original_day
        ps.status = "planned"
    ps.original_day = None
    _event(db, user, ps.id, "undone", {"was": was, "title": ps.title or ps.label})
    await db.commit()
    return {"saved": True, "view": await full_view(db, user)}


# ---------------------------------------------------------------- moving, editing, adding, removing
@router.post("/items/{item_id}/move")
async def move(item_id: str, body: MoveIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    ps = await _own_block(db, user, item_id)
    if ps.status in ("done", "partial", "skipped"):
        raise HTTPException(status.HTTP_409_CONFLICT, "A confirmed block cannot be moved. Undo it first.")
    core = await store.load_core(db, user)
    _check_day(body.day, core.now.date())
    warning = None
    if ps.task_id:
        row = next((r for r in core.tasks if r.id == str(ps.task_id)), None)
        if row is not None and body.day > row.deadline.astimezone(C.tz_of(core.settings)).date():
            warning = "That day is after the deadline of this task."
    _event(db, user, ps.id, "moved", {"from": ps.day.isoformat(), "to": body.day.isoformat(), "title": ps.title or ps.label})
    ps.original_day = ps.original_day or ps.day
    ps.day, ps.status, ps.manual = body.day, ("delayed" if ps.status in ("planned", "missed", "not_done") else ps.status), True
    await db.commit()
    return {"saved": True, "warning": warning, "view": await full_view(db, user)}


@router.patch("/items/{item_id}")
async def edit(item_id: str, body: EditIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    ps = await _own_block(db, user, item_id)
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Nothing to change.")
    if ps.status in ("done", "partial") and ("minutes" in patch or "day" in patch):
        raise HTTPException(status.HTTP_409_CONFLICT, "A confirmed block keeps its minutes and day. Undo it first.")
    core = await store.load_core(db, user)
    if "day" in patch:
        _check_day(patch["day"], core.now.date())
    before = {k: (getattr(ps, k).isoformat() if k == "day" else getattr(ps, k)) for k in ("title", "subject", "label", "method", "minutes", "day") if k in patch}
    if "title" in patch:
        ps.title = patch["title"]
    if "subject" in patch:
        ps.subject = patch["subject"]
    if "label" in patch:
        ps.label = patch["label"]
    if "method" in patch:
        ps.method = patch["method"]
    if "minutes" in patch:
        ps.minutes = patch["minutes"]
    if "day" in patch and patch["day"] != ps.day:
        ps.original_day = ps.original_day or ps.day
        ps.day = patch["day"]
    ps.manual = True
    _event(db, user, ps.id, "edited", {"before": before, "after": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in patch.items()}, "title": ps.title or ps.label})
    await db.commit()
    return {"saved": True, "view": await full_view(db, user)}


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def add(body: AddIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    plan = await store.active_plan(db, user.id)
    if plan is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Make your plan in Smart Planner first, then you can add your own study blocks here.")
    core = await store.load_core(db, user)
    _check_day(body.day, core.now.date())
    task_id = None
    if body.task_id:
        task = await db.get(Task, body.task_id)
        if task is None or task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
        task_id = task.id
    count = len((await db.scalars(select(PlanSession.id).where(PlanSession.user_id == user.id))).all())
    if count >= 3000:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your roadmap is very long. Remove some old blocks first.")
    position = 100 + len((await db.scalars(select(PlanSession.id).where(PlanSession.user_id == user.id, PlanSession.day == body.day))).all())
    ps = PlanSession(plan_id=plan.id, user_id=user.id, task_id=task_id, day=body.day, position=position, minutes=body.minutes, label=body.label or "My own study block",
                     method=body.method, status="planned", title=body.title, subject=body.subject, manual=True)
    db.add(ps)
    await db.flush()
    _event(db, user, ps.id, "added", {"title": body.title, "minutes": body.minutes, "day": body.day.isoformat(), "subject": body.subject})
    await db.commit()
    return {"saved": True, "id": str(ps.id), "view": await full_view(db, user)}


@router.delete("/items/{item_id}")
async def remove(item_id: str, confirm: bool = Query(default=False), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    ps = await _own_block(db, user, item_id)
    if not confirm:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please confirm that you want to remove this block.")
    if ps.status in ("done", "partial"):
        raise HTTPException(status.HTTP_409_CONFLICT, "A block you have confirmed is part of your history and cannot be removed.")
    _event(db, user, ps.id, "removed", {"title": ps.title or ps.label, "minutes": ps.minutes, "day": ps.day.isoformat(), "had_task": bool(ps.task_id)})
    await db.delete(ps)
    await db.commit()
    return {"saved": True, "note": "Removed. If this block belonged to a topic, a new plan will place that work again.", "view": await full_view(db, user)}


# ---------------------------------------------------------------- replanning
async def _preview(db: AsyncSession, user: User) -> tuple:
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    today = core.now.date()
    plan = await store.active_plan(db, user.id)
    if plan is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "There is no plan yet. Make one in Smart Planner first.")
    res = C.plan_for(core, alternatives=True)
    rows = (await db.scalars(select(PlanSession).where(PlanSession.user_id == user.id))).all()
    pending_ids = {r.id for r in core.tasks if r.status == "pending"}
    replaced = [r for r in rows if r.day >= today and r.status in ("planned", "delayed") and r.task_id is not None]
    kept_custom = [r for r in rows if r.day >= today and r.status in ("planned", "delayed") and r.task_id is None]
    missed = [r for r in rows if r.day < today and r.status == "planned"]
    edited = [r for r in replaced if r.manual]
    old_future = [{"day": r.day.isoformat(), "minutes": r.minutes} for r in replaced]
    pub = C.public_result(res)
    new_minutes = sum(d["planned"] for d in pub["days"])
    return core, res, {
        "can_apply": pub["feasibility"]["level"] != "empty",
        "feasibility": pub["feasibility"],
        "keeps": {"done": sum(1 for r in rows if r.status == "done"), "partial": sum(1 for r in rows if r.status == "partial"),
                  "studied_minutes": sum(r.actual_minutes or 0 for r in rows if r.status in ("done", "partial")),
                  "own_blocks": len(kept_custom), "text": "Everything you already confirmed stays in your history."},
        "replaces": {"blocks": len(replaced), "minutes": sum(r.minutes for r in replaced)},
        "becomes_missed": {"blocks": len(missed), "minutes": sum(r.minutes for r in missed)},
        "new_plan": {"minutes": new_minutes, "days": len([d for d in pub["days"] if d["sessions"]]), "tasks": len(pending_ids)},
        "edited_blocks": [{"id": str(r.id), "title": r.title or r.label, "day": r.day.isoformat(), "minutes": r.minutes} for r in edited][:20],
        "changes": C.diff_plans(old_future, res, today.isoformat()),
        "notes": pub.get("notes", []),
        "warning": (f"{len(edited)} block{'s' if len(edited) != 1 else ''} you changed by hand will be replaced by the new plan. You can cancel and keep them." if edited else None),
    }


@router.post("/replan/preview")
async def replan_preview(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _, _, prev = await _preview(db, user)
    return prev


@router.post("/replan/apply")
async def replan_apply(body: ReplanIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if not body.confirm:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please confirm that you want to replace your remaining plan.")
    core, res, prev = await _preview(db, user)
    if not prev["can_apply"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "There is nothing left to plan.")
    await store.store_plan(db, user, core, res, body.reason)
    _event(db, user, None, "replan", {"replaced_blocks": prev["replaces"]["blocks"], "new_minutes": prev["new_plan"]["minutes"], "kept_done": prev["keeps"]["done"],
                                       "reason": body.reason, "edited_replaced": len(prev["edited_blocks"])})
    await db.commit()
    return {"saved": True, "summary": prev, "view": await full_view(db, user)}


# ================================================================= guests (nothing is stored on the server)
from fastapi import Request  # noqa: E402

from . import routes as _routes  # noqa: E402
from .settings_schema import settings_from  # noqa: E402

demo_router = APIRouter(prefix="/demo/assist", tags=["my tasks (guest mode)"])


class GuestBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    task_id: Optional[str] = Field(default=None, max_length=64)
    day: date
    position: int = Field(default=0, ge=0, le=1000)
    minutes: int = Field(ge=5, le=600)
    actual_minutes: int = Field(default=0, ge=0, le=600)
    break_after: int = Field(default=0, ge=0, le=60)
    label: str = Field(default="", max_length=200)
    method: str = Field(default="", max_length=400)
    start_hint: Optional[str] = Field(default=None, max_length=5)
    status: Literal["planned", "done", "partial", "not_done", "delayed", "skipped", "missed"] = "planned"
    title: Optional[str] = Field(default=None, max_length=200)
    subject: Optional[str] = Field(default=None, max_length=100)
    manual: bool = False
    original_day: Optional[date] = None
    felt: Optional[Literal["easy", "okay", "difficult"]] = None
    completed_at: Optional[str] = Field(default=None, max_length=40)


class GuestTaskRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    subject: Optional[str] = Field(default=None, max_length=100)
    deadline: date
    status: Literal["pending", "completed"] = "pending"


class GuestRoadmapIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    today: date
    time: str = Field(default="12:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    name: str = Field(default="", max_length=60)
    settings: dict = Field(default_factory=dict)
    blocks: list[GuestBlock] = Field(default_factory=list, max_length=1500)
    tasks: list[GuestTaskRow] = Field(default_factory=list, max_length=60)


@demo_router.post("/roadmap")
async def demo_roadmap(body: GuestRoadmapIn, request: Request) -> dict:
    """The same page numbers for a guest: the browser sends its own roadmap, the same pure code answers, nothing is stored here."""
    _routes._guest_rate(request, calc_only=True)
    st = settings_from(body.settings)
    blocks = [{**b.model_dump(mode="json"), "day": b.day.isoformat(), "original_day": b.original_day.isoformat() if b.original_day else None} for b in body.blocks]
    tasks = [{**t.model_dump(mode="json"), "deadline": t.deadline.isoformat()} for t in body.tasks]
    view = RV.build_view(blocks, tasks, body.today)
    view["time_zone"] = st.timezone
    view["reminders"] = RM.summary_for(view, body.today)
    now = datetime.fromisoformat(f"{body.today.isoformat()}T{body.time}:00")
    view["reminders_due"] = RM.compute(view, st, now, body.name.split(" ")[0] if body.name else "")
    for r in view["reminders_due"]:
        r["due_on"] = r["due_on"].isoformat() if r["due_on"] else None
    return view
