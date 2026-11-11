"""
HTTP routes for the task-aware engine.

  POST /smart/plan          (logged in)  analyse a task and return questions or a plan; history comes from the database
  POST /demo/smart/plan     (guest)      same engine; the browser sends its own small history summary, nothing is stored
  POST /smart/outcome       how long a finished task really took (the engine learns from it)
  POST /smart/session       one logged study session
  GET  /smart/learned       what MindSync has learned about this student (per kind of work)
  PUT  /smart/skills/{kind} the student's own experience rating

Only numbers and kinds of work are stored, never the task text. All inputs are bounded and validated.
"""
from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import SessionLog, TaskOutcome, User, UserSkill

from . import history as H
from . import taxonomy as T
from .engine import PlanInput, run

router = APIRouter(prefix="/smart", tags=["task-aware planning"])
demo_router = APIRouter(prefix="/demo/smart", tags=["task-aware planning (guest mode)"])

ANSWER_KEYS = {"kind", "scope", "progress", "skill", "deadline", "daily_minutes", "prior", "resources", "size", "grasp"}
KindName = Literal["programming", "mathematics", "writing", "exam", "reading", "presentation", "data", "admin", "general"]


class OutcomeIn(BaseModel):
    kind: KindName
    raw_minutes: int = Field(ge=1, le=6000)
    actual_minutes: int = Field(ge=1, le=6000)
    felt: Optional[int] = Field(default=None, ge=1, le=5)
    predicted_personal: Optional[float] = Field(default=None, ge=1, le=5)


class SessionIn(BaseModel):
    kind: KindName
    minutes: int = Field(ge=5, le=600)
    completed: bool
    focus: Optional[int] = Field(default=None, ge=1, le=5)


class HistoryIn(BaseModel):
    outcomes: list[OutcomeIn] = Field(default_factory=list, max_length=200)
    sessions: list[SessionIn] = Field(default_factory=list, max_length=300)


class SmartPlanIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=2000)
    deadline: Optional[date] = None
    deadline_hour: Optional[int] = Field(default=None, ge=0, le=23)
    today: Optional[date] = None
    daily_minutes: Optional[int] = Field(default=None, ge=15, le=720)
    today_minutes: Optional[int] = Field(default=None, ge=0, le=720)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    stress_risk: Optional[Literal["Low", "Medium", "High"]] = None
    answers: dict[str, Any] = Field(default_factory=dict)
    skipped: list[str] = Field(default_factory=list, max_length=8)
    skills: dict[KindName, int] = Field(default_factory=dict)           # guests send their saved ratings
    history: Optional[HistoryIn] = None                                  # guests send their own history

    @field_validator("title", "details")
    @classmethod
    def _tidy(cls, v: str) -> str:
        return " ".join(v.split()) if "\n" not in v else "\n".join(" ".join(line.split()) for line in v.splitlines()).strip()

    @field_validator("answers")
    @classmethod
    def _answers(cls, v: dict) -> dict:
        if len(v) > 10:
            raise ValueError("Too many answers")
        clean = {}
        for k, val in v.items():
            if k not in ANSWER_KEYS:
                raise ValueError(f"Unknown answer: {k}")
            if isinstance(val, bool) or not isinstance(val, (str, int, float)):
                raise ValueError("Answers must be text or numbers")
            if isinstance(val, str) and len(val) > 2000:
                raise ValueError("Answer too long")
            clean[k] = val
        if "kind" in clean and clean["kind"] not in T.KINDS:
            raise ValueError("Unknown kind")
        return clean

    @field_validator("skipped")
    @classmethod
    def _skipped(cls, v: list) -> list:
        return [s for s in v if s in ANSWER_KEYS]

    @field_validator("skills")
    @classmethod
    def _skills(cls, v: dict) -> dict:
        for level in v.values():
            if not 1 <= level <= 5:
                raise ValueError("Skill must be 1-5")
        return v


def _today(client_day: Optional[date]) -> date:
    server = datetime.now(timezone.utc).date()
    if client_day and abs((client_day - server).days) <= 1:      # the student's own calendar day (time zones)
        return client_day
    return server


def _to_input(body: SmartPlanIn, skills: dict, outcomes: list, sessions: list) -> PlanInput:
    return PlanInput(title=body.title, details=body.details, deadline=body.deadline, deadline_hour=body.deadline_hour,
                     today=_today(body.today), daily_minutes=body.daily_minutes, today_minutes=body.today_minutes,
                     energy=body.energy, stress_risk=body.stress_risk, answers=body.answers, skipped=body.skipped,
                     skills=skills, outcomes=outcomes, sessions=sessions)


def _history_objs(rows_o, rows_s):
    return ([H.Outcome(o.kind, o.raw_minutes, o.actual_minutes, o.felt, o.predicted_personal) for o in rows_o],
            [H.SessionRecord(s.kind, s.minutes, s.completed, s.focus) for s in rows_s])


@router.post("/plan")
async def smart_plan(body: SmartPlanIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    skills = {s.kind: s.level for s in (await db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))).all()}
    outcomes = (await db.scalars(select(TaskOutcome).where(TaskOutcome.user_id == user.id)
                                 .order_by(TaskOutcome.created_at.desc()).limit(200))).all()
    sessions = (await db.scalars(select(SessionLog).where(SessionLog.user_id == user.id)
                                 .order_by(SessionLog.created_at.desc()).limit(300))).all()
    o, s = _history_objs(outcomes, sessions)
    result = run(_to_input(body, skills, o, s))
    # remember the experience rating the student just gave, so they are not asked again
    given = body.answers.get("skill")
    if result.get("status") == "plan" and str(given).isdigit() and 1 <= int(given) <= 5:
        kind = result["inputs_used"]["skill_kind"]
        row = await db.get(UserSkill, (user.id, kind))
        if row is None:
            db.add(UserSkill(user_id=user.id, kind=kind, level=int(given)))
        else:
            row.level = int(given)
        await db.commit()
    return result


@demo_router.post("/plan")
async def demo_smart_plan(body: SmartPlanIn, request: Request) -> dict:
    from app.demo import _check as demo_rate_check          # imported here: app.demo itself imports this module
    demo_rate_check(request)
    h = body.history or HistoryIn()
    o, s = _history_objs(h.outcomes, h.sessions)
    return run(_to_input(body, dict(body.skills), o, s))


@router.post("/outcome", status_code=status.HTTP_201_CREATED)
async def add_outcome(body: OutcomeIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    db.add(TaskOutcome(user_id=user.id, **body.model_dump()))
    await db.commit()
    return {"saved": True}


@router.post("/session", status_code=status.HTTP_201_CREATED)
async def add_session(body: SessionIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    db.add(SessionLog(user_id=user.id, **body.model_dump()))
    await db.commit()
    return {"saved": True}


def learned_summary(skills: dict, outcomes: list, sessions: list) -> dict:
    kinds = sorted({o.kind for o in outcomes} | {s.kind for s in sessions} | set(skills))
    out = []
    for k in kinds:
        cal = H.calibration(k, outcomes)
        mine = [o for o in outcomes if o.kind == k]
        pref = H.preferred_session(k, sessions, 40)
        out.append({"kind": k, "label": T.KINDS[k]["label"], "skill": skills.get(k), "tasks_logged": len(mine),
                    "typical_ratio": cal["typical_ratio"] if cal["basis"] == "kind" else None,
                    "estimate_adjustment_percent": round((cal["factor"] - 1) * 100) if cal["basis"] == "kind" else 0,
                    "sessions_logged": len([s for s in sessions if s.kind == k]),
                    "preferred_session": pref})
    return {"kinds": out, "total_outcomes": len(outcomes), "total_sessions": len(sessions)}


@router.get("/learned")
async def learned(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    skills = {s.kind: s.level for s in (await db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))).all()}
    outcomes = (await db.scalars(select(TaskOutcome).where(TaskOutcome.user_id == user.id))).all()
    sessions = (await db.scalars(select(SessionLog).where(SessionLog.user_id == user.id))).all()
    o, s = _history_objs(outcomes, sessions)
    return learned_summary(skills, o, s)


@router.put("/skills/{kind}")
async def set_skill(kind: KindName, level: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if not 1 <= level <= 5:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Level must be 1 to 5")
    row = await db.get(UserSkill, (user.id, kind))
    if row is None:
        db.add(UserSkill(user_id=user.id, kind=kind, level=level))
    else:
        row.level = level
    await db.commit()
    return {"kind": kind, "level": level}
