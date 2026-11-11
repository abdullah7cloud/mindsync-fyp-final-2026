"""Request models. Every field is bounded; free text is cleaned; guests send their own state in the same shapes."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.ai.sanitize import clean_text
from app.taskaware import history as H
from app.taskaware import taxonomy as T
from app.taskaware.routes import ANSWER_KEYS, HistoryIn, KindName

from . import core as C
from .formplan import PlanFormIn
from .settings_schema import profile_from, settings_from

SIZE = Literal["tiny", "small", "medium", "large", "huge"]


class AiEstimate(BaseModel):
    low: Optional[int] = Field(default=None, ge=5, le=6000)
    likely: Optional[int] = Field(default=None, ge=5, le=6000)
    high: Optional[int] = Field(default=None, ge=5, le=6000)


class SubtaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    share_percent: int = Field(ge=1, le=100)
    how: str = Field(default="", max_length=300)


class DraftIn(BaseModel):
    ref: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=200)
    details: str = Field(default="", max_length=2000)
    deadline_date: Optional[date] = None
    deadline_hour: Optional[int] = Field(default=None, ge=0, le=23)
    kind: Optional[KindName] = None
    felt_hard: Optional[int] = Field(default=None, ge=1, le=5)
    answers: dict[str, Any] = Field(default_factory=dict)
    ai_estimate: Optional[AiEstimate] = None
    subtasks: list[SubtaskIn] = Field(default_factory=list, max_length=8)
    priority: int = Field(default=2, ge=1, le=3)

    @field_validator("title", "details")
    @classmethod
    def _clean(cls, v: str) -> str:
        return clean_text(v, 2000)

    @field_validator("answers")
    @classmethod
    def _answers(cls, v: dict) -> dict:
        if len(v) > 10:
            raise ValueError("Too many answers")
        out = {}
        for k, val in v.items():
            if k not in ANSWER_KEYS:
                raise ValueError(f"Unknown answer: {k}")
            if isinstance(val, bool) or not isinstance(val, (str, int, float)):
                raise ValueError("Answers must be text or numbers")
            if isinstance(val, str) and len(val) > 2000:
                raise ValueError("Answer too long")
            out[k] = clean_text(val, 2000) if isinstance(val, str) else val
        if "kind" in out and out["kind"] not in T.KINDS:
            raise ValueError("Unknown kind")
        return out

    def to_core(self) -> C.Draft:
        est = self.ai_estimate.model_dump() if self.ai_estimate else None
        subs = [s.model_dump() for s in self.subtasks] if 3 <= len(self.subtasks) <= 8 else []
        return C.Draft(ref=self.ref, title=self.title, deadline_date=self.deadline_date, deadline_hour=self.deadline_hour, details=self.details,
                       kind=self.kind, felt_hard=self.felt_hard, answers=dict(self.answers), ai_estimate=est, subtasks=subs, priority=self.priority)


class UnderstandFields(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    deadline_date: Optional[date] = None
    deadline_hour: Optional[int] = Field(default=None, ge=0, le=23)
    kind: Optional[KindName] = None
    felt_hard: Optional[int] = Field(default=None, ge=1, le=5)
    size: Optional[SIZE] = None


class UnderstandIn(BaseModel):
    text: str = Field(default="", max_length=3000)
    fields: UnderstandFields = Field(default_factory=UnderstandFields)

    @field_validator("text")
    @classmethod
    def _t(cls, v: str) -> str:
        return clean_text(v, 3000)


class EvaluateIn(BaseModel):
    drafts: list[DraftIn] = Field(default_factory=list, max_length=40)
    today_minutes: Optional[int] = Field(default=None, ge=0, le=720)


class SessionFeedbackIn(BaseModel):
    plan_session_id: Optional[str] = Field(default=None, max_length=64)
    task_id: Optional[str] = Field(default=None, max_length=64)
    status: Literal["done", "partial", "stopped", "skipped"] = "done"
    felt: Optional[Literal["easy", "okay", "difficult"]] = None
    planned_minutes: int = Field(default=0, ge=0, le=600)
    actual_minutes: int = Field(default=0, ge=0, le=600)
    focus: Optional[int] = Field(default=None, ge=1, le=5)
    felt_difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    energy_after: Optional[int] = Field(default=None, ge=1, le=5)
    length_feel: Optional[Literal["short", "right", "long"]] = None
    task_done: bool = False
    remaining_minutes: Optional[int] = Field(default=None, ge=0, le=6000)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _q(cls, v: str) -> str:
        v = clean_text(v, 500)
        if not v:
            raise ValueError("Please type a question")
        return v


class TaskPlanPatch(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    remaining_minutes: Optional[int] = Field(default=None, ge=0, le=6000)


class ReplanApplyIn(BaseModel):
    reason: Literal["energy", "deadline", "settings", "behind", "tasks", "wellbeing", "manual"] = "manual"


# ---------------------------------------------------------------- guest state
class GuestMetaStage(BaseModel):
    work_id: str = Field(max_length=40)
    kind: KindName
    label: str = Field(max_length=120)
    method: str = Field(max_length=300)
    minutes: int = Field(ge=1, le=6000)
    deep: bool = True
    session: list[int] = Field(min_length=3, max_length=3)
    breaks: bool = True

    @field_validator("work_id")
    @classmethod
    def _w(cls, v: str) -> str:
        if v not in T.WORKS:
            raise ValueError("unknown step type")
        return v


class GuestMeta(BaseModel):
    kind: KindName
    kind_label: str = Field(default="", max_length=60)
    intrinsic: float = Field(ge=1, le=5)
    personal: float = Field(ge=1, le=5)
    low: int = Field(ge=0, le=6000)
    likely: int = Field(ge=0, le=6000)
    high: int = Field(ge=0, le=6000)
    done: int = Field(default=0, ge=0, le=6000)
    stages: list[GuestMetaStage] = Field(max_length=12)
    source: Literal["rules", "ai", "blended"] = "rules"
    priority: int = Field(default=2, ge=1, le=3)
    confidence: str = Field(default="medium", max_length=10)
    uncertainty: float = Field(default=0.3, ge=0, le=1)
    difficulty_label: str = Field(default="", max_length=40)
    difficulty_text: str = Field(default="", max_length=400)
    workload_text: str = Field(default="", max_length=600)
    understanding: str = Field(default="", max_length=400)
    uncertainties: list[str] = Field(default_factory=list, max_length=8)
    basis: str = Field(default="size", max_length=20)
    size: str = Field(default="medium", max_length=10)
    skill_kind: str = Field(default="general", max_length=20)
    # what the Smart Planner form remembers about the topic (see formplan.py)
    topic_id: Optional[str] = Field(default=None, max_length=40)
    subject: Optional[str] = Field(default=None, max_length=60)
    task_type: Optional[str] = Field(default=None, max_length=20)
    progress: Optional[str] = Field(default=None, max_length=10)
    grasp: Optional[int] = Field(default=None, ge=1, le=4)
    form_sig: Optional[str] = Field(default=None, max_length=20)
    actual_before: int = Field(default=0, ge=0, le=60000)
    raw_likely: Optional[int] = Field(default=None, ge=0, le=60000)
    form_desc: str = Field(default="", max_length=600)
    details: dict = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def _details(cls, v: dict) -> dict:
        from .formplan import TopicDetails
        return TopicDetails(**v).model_dump(exclude_none=True) if v else {}


class GuestTask(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="general", max_length=100)
    difficulty: int = Field(default=3, ge=1, le=5)
    deadline: datetime
    status: Literal["pending", "completed"] = "pending"
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    meta: Optional[GuestMeta] = None


class GuestSession(BaseModel):
    task_id: Optional[str] = Field(default=None, max_length=64)
    kind: KindName = "general"
    planned_minutes: int = Field(default=0, ge=0, le=600)
    actual_minutes: int = Field(ge=1, le=600)
    completed: bool = True
    focus: Optional[int] = Field(default=None, ge=1, le=5)
    felt_difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    length_feel: Optional[Literal["short", "right", "long"]] = None
    created_at: datetime


class GuestCheckin(BaseModel):
    energy_level: int = Field(ge=1, le=5)
    created_at: datetime


class GuestWellbeing(BaseModel):
    label: Literal["Low", "Medium", "High"]
    created_at: datetime


class GuestPlanSession(BaseModel):
    day: date
    task_id: Optional[str] = Field(default=None, max_length=64)
    minutes: int = Field(ge=1, le=600)
    status: Literal["planned", "done", "skipped"] = "planned"


class GuestActivePlan(BaseModel):
    inputs: dict
    future: list[GuestPlanSession] = Field(default_factory=list, max_length=400)
    past: list[GuestPlanSession] = Field(default_factory=list, max_length=400)


class GuestState(BaseModel):
    now: datetime
    settings: dict = Field(default_factory=dict)
    profile: dict = Field(default_factory=dict)
    tasks: list[GuestTask] = Field(default_factory=list, max_length=60)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    stress: Optional[Literal["Low", "Medium", "High"]] = None
    skills: dict[KindName, int] = Field(default_factory=dict)
    history: HistoryIn = Field(default_factory=HistoryIn)
    studied_today: int = Field(default=0, ge=0, le=720)
    task_sessions: list[GuestSession] = Field(default_factory=list, max_length=300)
    checkins: list[GuestCheckin] = Field(default_factory=list, max_length=60)
    wellbeing: list[GuestWellbeing] = Field(default_factory=list, max_length=10)
    plan_sessions: list[GuestPlanSession] = Field(default_factory=list, max_length=400)
    active_plan: Optional[GuestActivePlan] = None

    @field_validator("skills")
    @classmethod
    def _sk(cls, v: dict) -> dict:
        if any(not 1 <= x <= 5 for x in v.values()):
            raise ValueError("Skill must be 1-5")
        return v


class GuestUnderstandIn(UnderstandIn):
    today: date
    time_zone: str = Field(default="UTC", max_length=60)
    settings: dict = Field(default_factory=dict)


class GuestEvaluateIn(EvaluateIn):
    state: GuestState


class GuestAskIn(AskIn):
    state: GuestState


class GuestDashboardIn(BaseModel):
    state: GuestState


class GuestReplanIn(BaseModel):
    state: GuestState


class GuestPlanFormIn(BaseModel):
    state: GuestState
    form: PlanFormIn


def aware(dt: datetime, tz) -> datetime:
    return dt.astimezone(tz) if dt.tzinfo else dt.replace(tzinfo=tz)


def guest_core(state: GuestState) -> C.CoreInput:
    """Turn what a guest's browser sent into the same input the database path produces."""
    settings = settings_from(state.settings)
    tz = C.tz_of(settings)
    server_now = datetime.now(timezone.utc)
    now = aware(state.now, tz)
    if abs((now - server_now).total_seconds()) > 36 * 3600:        # a wrong or forged clock cannot move the plan by days
        now = server_now.astimezone(tz)
    rows = []
    for t in state.tasks:
        meta = t.meta.model_dump() if t.meta else None
        rows.append(C.TaskRow(id=t.id, title=clean_text(t.title, 200), deadline=aware(t.deadline, tz), status=t.status,
                              description=clean_text(t.description, 2000), category=t.category, difficulty=t.difficulty,
                              created_at=t.created_at, completed_at=t.completed_at, meta=meta))
    outcomes = [H.Outcome(o.kind, o.raw_minutes, o.actual_minutes, o.felt, o.predicted_personal) for o in state.history.outcomes]
    sessions = [H.SessionRecord(s.kind, s.minutes, s.completed, s.focus) for s in state.history.sessions]
    recent = sorted(state.task_sessions, key=lambda s: s.created_at, reverse=True)
    core = C.CoreInput(now=now, settings=settings, tasks=rows, profile=profile_from(state.profile), energy=state.energy, stress=state.stress,
                       skills=dict(state.skills), outcomes=outcomes, sessions=sessions, studied_today=state.studied_today,
                       length_bias=C.length_bias_from([(s.kind, s.length_feel) for s in recent]))
    return C.apply_mood(core)
