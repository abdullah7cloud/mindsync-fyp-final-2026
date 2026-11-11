"""
Study Planner and Dashboard API.

    POST   /study/plans              make a plan from the form (AI online, built-in engine offline)
    GET    /study/plans              all plans with their tasks
    PATCH  /study/plans/{id}         edit the plan (subject, topic, notes, target date, roadmap)
    DELETE /study/plans/{id}         delete the plan and its tasks
    PATCH  /study/tasks/{id}         edit a task or tick it done / not done
    DELETE /study/tasks/{id}
    GET    /study/dashboard          totals, progress, deadlines, overdue tasks, task list

Every query is filtered by the signed-in student's id, so one student can never read or change another student's plan.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import service as ai
from app.ai.sanitize import clean_text
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.ratelimit import LoginRateLimiter

from . import planner as PL
from .models import SPlan, STask

router = APIRouter(prefix="/study", tags=["study planner"])
_plan_limit = LoginRateLimiter(max_failures=8, window_seconds=600)
MAX_PLANS = 30
MAX_TASKS_TOTAL = 600
_HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def _tz_name(tz: Optional[str]) -> str:
    z = PL.zone(tz or "UTC")
    return z.key


def _today(tz: Optional[str]) -> date:
    return datetime.now(PL.zone(tz or "UTC")).date()


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=1, max_length=80)
    topic: str = Field(min_length=1, max_length=120)
    goal: str = Field(default="", max_length=1500)
    target_date: date
    mood: Literal["good", "okay", "tired"] = "okay"
    stress: Literal["low", "medium", "high"] = "medium"
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("subject", "topic")
    @classmethod
    def _one_line(cls, v: str) -> str:
        v = " ".join(clean_text(v, 200).split())
        if not v:
            raise ValueError("This cannot be empty")
        return v

    @field_validator("goal")
    @classmethod
    def _goal(cls, v: str) -> str:
        return clean_text(v, 1500)


class RoadmapStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=80)
    text: str = Field(default="", max_length=260)

    @field_validator("title", "text")
    @classmethod
    def _c(cls, v: str) -> str:
        return clean_text(v, 260)


class PlanPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: Optional[str] = Field(default=None, min_length=1, max_length=80)
    topic: Optional[str] = Field(default=None, min_length=1, max_length=120)
    goal: Optional[str] = Field(default=None, max_length=1500)
    target_date: Optional[date] = None
    roadmap: Optional[list[RoadmapStep]] = Field(default=None, max_length=10)
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("subject", "topic")
    @classmethod
    def _one_line(cls, v):
        if v is None:
            return v
        v = " ".join(clean_text(v, 200).split())
        if not v:
            raise ValueError("This cannot be empty")
        return v

    @field_validator("goal")
    @classmethod
    def _goal(cls, v):
        return None if v is None else clean_text(v, 1500)

    @model_validator(mode="after")
    def _something(self):
        if all(getattr(self, k) is None for k in ("subject", "topic", "goal", "target_date", "roadmap")):
            raise ValueError("Nothing to change")
        return self


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)
    details: Optional[str] = Field(default=None, max_length=400)
    due_date: Optional[date] = None
    start_time: Optional[str] = Field(default=None, pattern=_HHMM)
    clear_time: bool = False
    minutes: Optional[int] = Field(default=None, ge=5, le=480)
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def _t(cls, v):
        if v is None:
            return v
        v = " ".join(clean_text(v, 200).split())
        if not v:
            raise ValueError("The title cannot be empty")
        return v

    @field_validator("details")
    @classmethod
    def _d(cls, v):
        return None if v is None else clean_text(v, 400)

    @field_validator("due_date")
    @classmethod
    def _range(cls, v):
        if v is not None and not date(2000, 1, 1) <= v <= date(2100, 1, 1):
            raise ValueError("Choose a sensible date")
        return v


def task_out(t: STask, subject: str = "") -> dict:
    return {"id": str(t.id), "plan_id": str(t.plan_id), "subject": subject, "title": t.title, "details": t.details, "due_date": t.due_date.isoformat(),
            "start_time": t.start_time, "minutes": t.minutes, "done": t.done}


def plan_out(p: SPlan, tasks: list) -> dict:
    return {"id": str(p.id), "subject": p.subject, "topic": p.topic, "goal": p.goal, "target_date": p.target_date.isoformat(), "mood": p.mood, "stress": p.stress,
            "roadmap": p.roadmap, "source": p.source, "note": p.note, "created_at": p.created_at.isoformat(),
            "tasks": [task_out(t, p.subject) for t in sorted(tasks, key=lambda x: (x.due_date, x.start_time or "99:99", x.position))],
            "done": sum(1 for t in tasks if t.done), "total": len(tasks)}


async def _own_plan(db: AsyncSession, user: User, plan_id: uuid.UUID) -> SPlan:
    p = await db.get(SPlan, plan_id)
    if p is None or p.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    return p


async def _own_task(db: AsyncSession, user: User, task_id: uuid.UUID) -> STask:
    t = await db.get(STask, task_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return t


async def _tasks_of(db: AsyncSession, user: User, plan_ids: Optional[list] = None) -> list:
    q = select(STask).where(STask.user_id == user.id)
    if plan_ids is not None:
        q = q.where(STask.plan_id.in_(plan_ids))
    return list((await db.execute(q)).scalars())


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_plan(body: PlanIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    wait = _plan_limit.retry_after(str(user.id))
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You made several plans very quickly. Please wait a moment.", headers={"Retry-After": str(wait)})
    _plan_limit.record_failure(str(user.id))
    tz = _tz_name(body.timezone)
    today = _today(tz)
    if body.target_date < today:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The target date must be today or a day in the future.")
    if body.target_date > today + timedelta(days=366):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please choose a target date within one year.")
    n_plans = int(await db.scalar(select(func.count()).select_from(SPlan).where(SPlan.user_id == user.id)) or 0)
    n_tasks = int(await db.scalar(select(func.count()).select_from(STask).where(STask.user_id == user.id)) or 0)
    if n_plans >= MAX_PLANS or n_tasks >= MAX_TASKS_TOTAL:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have a lot of plans already. Please delete one you no longer need.")
    form = PL.Form(subject=body.subject, topic=body.topic, goal=body.goal, target=body.target_date, mood=body.mood, stress=body.stress, tz=tz)
    ctx = ai.AICtx(db=db, user_id=user.id, student_allows=True)
    made = await PL.make_plan(ctx, form, datetime.now(timezone.utc))
    plan = SPlan(user_id=user.id, subject=body.subject, topic=body.topic, goal=body.goal, target_date=body.target_date, mood=body.mood, stress=body.stress,
                 roadmap=made["roadmap"], source=made["source"], note=made["note"][:300])
    db.add(plan)
    await db.flush()
    rows = [STask(user_id=user.id, plan_id=plan.id, position=i, title=t["title"][:160], details=t["details"][:400], due_date=date.fromisoformat(t["due_date"]),
                  start_time=t.get("start_time"), minutes=int(t["minutes"])) for i, t in enumerate(made["tasks"])]
    db.add_all(rows)
    await db.commit()
    return plan_out(plan, rows)


@router.get("/plans")
async def list_plans(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    plans = list((await db.execute(select(SPlan).where(SPlan.user_id == user.id).order_by(SPlan.created_at.desc()))).scalars())
    tasks = await _tasks_of(db, user)
    by: dict = {}
    for t in tasks:
        by.setdefault(t.plan_id, []).append(t)
    return {"plans": [plan_out(p, by.get(p.id, [])) for p in plans]}


@router.patch("/plans/{plan_id}")
async def edit_plan(plan_id: uuid.UUID, body: PlanPatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _own_plan(db, user, plan_id)
    if body.target_date is not None and body.target_date != p.target_date:
        if body.target_date < _today(_tz_name(body.timezone)):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The target date must be today or a day in the future.")
        if body.target_date > date.today() + timedelta(days=400):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please choose a target date within one year.")
        p.target_date = body.target_date
    for k in ("subject", "topic", "goal"):
        v = getattr(body, k)
        if v is not None:
            setattr(p, k, v)
    if body.roadmap is not None:
        p.roadmap = [{"title": r.title, "text": r.text} for r in body.roadmap]
    await db.commit()
    tasks = await _tasks_of(db, user, [p.id])
    out = plan_out(p, tasks)
    late = [t for t in tasks if not t.done and t.due_date > p.target_date]
    out["warning"] = (f"{len(late)} task{'s are' if len(late) != 1 else ' is'} planned after the new target date. Change the date of "
                      f"{'those tasks' if len(late) != 1 else 'that task'}, or make a new plan.") if late else ""
    return out


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    p = await _own_plan(db, user, plan_id)
    await db.execute(delete(STask).where(STask.plan_id == p.id, STask.user_id == user.id))
    await db.delete(p)
    await db.commit()


@router.patch("/tasks/{task_id}")
async def edit_task(task_id: uuid.UUID, body: TaskPatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    t = await _own_task(db, user, task_id)
    if body.title is not None:
        t.title = body.title
    if body.details is not None:
        t.details = body.details
    if body.due_date is not None:
        t.due_date = body.due_date
    if body.clear_time:
        t.start_time = None
    elif body.start_time is not None:
        t.start_time = body.start_time
    if body.minutes is not None:
        t.minutes = body.minutes
    if body.done is not None and body.done != t.done:
        t.done = body.done
        t.done_at = datetime.now(timezone.utc) if body.done else None
    await db.commit()
    p = await db.get(SPlan, t.plan_id)
    return task_out(t, p.subject if p else "")


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    t = await _own_task(db, user, task_id)
    await db.delete(t)
    await db.commit()


@router.get("/dashboard")
async def dashboard(tz: str = Query(default="UTC", max_length=64), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    today = _today(_tz_name(tz))
    plans = list((await db.execute(select(SPlan).where(SPlan.user_id == user.id))).scalars())
    tasks = await _tasks_of(db, user)
    subj = {p.id: p.subject for p in plans}
    total = len(tasks)
    done = sum(1 for t in tasks if t.done)
    remaining = total - done
    progress = round(100 * done / total) if total else 0
    ordered = sorted(tasks, key=lambda t: (t.done, t.due_date, t.start_time or "99:99", t.position))
    overdue = [t for t in ordered if not t.done and t.due_date < today]
    deadlines = []
    for p in plans:
        mine = [t for t in tasks if t.plan_id == p.id]
        left = sum(1 for t in mine if not t.done)
        if left and p.target_date >= today:
            deadlines.append({"plan_id": str(p.id), "subject": p.subject, "topic": p.topic, "target_date": p.target_date.isoformat(),
                              "days_left": (p.target_date - today).days, "left": left, "total": len(mine)})
    deadlines.sort(key=lambda d: d["target_date"])
    return {"today": today.isoformat(), "total": total, "completed": done, "remaining": remaining, "progress": progress,
            "deadlines": deadlines[:6], "overdue": [{**task_out(t, subj.get(t.plan_id, "")), "days_late": (today - t.due_date).days} for t in overdue[:20]],
            "tasks": [task_out(t, subj.get(t.plan_id, "")) for t in ordered[:300]],
            "note": "Progress counts finished study tasks. It shows effort, not how well you understand the subject."}
