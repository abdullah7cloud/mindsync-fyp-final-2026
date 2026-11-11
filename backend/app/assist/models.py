"""
New tables for the connected planner. They are all NEW tables (created by create_all at start-up); no existing table is
altered, so an existing database keeps working. Only numbers, kinds of work and the student's own settings are stored
here, with two exceptions that are task text the student typed themselves: task_meta.subtasks (step names) and the
cached AI text in weekly_reviews / study_plans.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fk_user(index: bool = True):
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=index)


class UserSettings(Base):
    """The student's study settings as one validated JSON document (see assist/settings_schema.py)."""
    __tablename__ = "user_settings"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class UserProfile(Base):
    """What the student chose to tell MindSync about their studies (all optional)."""
    __tablename__ = "user_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class TaskMeta(Base):
    """Planning facts for one task: kind, difficulty, workload range, steps, and minutes already worked."""
    __tablename__ = "task_meta"
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = _fk_user()
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="general")
    intrinsic_difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    personal_difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    est_low: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    est_likely: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    est_high: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    done_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)       # the steps ("subtasks"), in order
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)            # explanation texts and uncertainty facts (display only)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="rules")  # rules | ai | blended
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)         # 1 low, 2 normal, 3 high (the student's choice)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    __table_args__ = (CheckConstraint("priority BETWEEN 1 AND 3", name="ck_taskmeta_priority"),)


class StudyPlan(Base):
    """One accepted plan. Older plans stay as history (status 'superseded')."""
    __tablename__ = "study_plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")     # active | superseded
    reason: Mapped[str] = mapped_column(String(30), nullable=False, default="new")        # new | energy | deadline | settings | missed | tasks | manual
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)             # feasibility, per-task, alternatives
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)              # snapshot used to detect when it is out of date
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class PlanSession(Base):
    """One planned study block on one day."""
    __tablename__ = "plan_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = _fk_user()
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    break_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    method: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    start_hint: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="planned")    # planned | done | partial | not_done | delayed | skipped | missed
    # --- My Tasks (added in update 24; older databases get these columns from database._MIGRATIONS) ---
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)       # time really studied on this block
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)               # own title of a block the student added or renamed
    subject: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)             # subject of a block that has no task
    manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)           # added or edited by the student (never silently overwritten)
    original_day: Mapped[Optional[date]] = mapped_column(Date, nullable=True)              # where a delayed block used to be
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    felt: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)                 # easy | okay | difficult
    __table_args__ = (CheckConstraint("minutes BETWEEN 5 AND 600", name="ck_plansession_minutes"),)


class PlanEvent(Base):
    """The history of a roadmap: every confirmation, edit, move, addition, removal and replan, in order."""
    __tablename__ = "plan_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    plan_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)   # no foreign key: history outlives a removed block
    kind: Mapped[str] = mapped_column(String(20), nullable=False)       # confirmed | undone | moved | edited | added | removed | replan | topic_added
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class Notification(Base):
    """In-app reminders. One row per (student, key): the key makes a reminder impossible to create twice."""
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    kind: Mapped[str] = mapped_column(String(12), nullable=False)       # daily | deadline
    key: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(600), nullable=False, default="")
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    due_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_notification_key"),)


class TaskSession(Base):
    """A study session the student really did (or abandoned), with their feedback. This is the learning signal."""
    __tablename__ = "task_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="general")
    planned_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)         # finished the block as planned
    focus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)                    # 1-5
    felt_difficulty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)          # 1-5
    energy_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)             # 1-5
    length_feel: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)            # short | right | long
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    __table_args__ = (CheckConstraint("actual_minutes BETWEEN 1 AND 600", name="ck_tasksession_minutes"),)


class AiUsage(Base):
    """Every language-model call (or refusal to call): what for, how much, how long, did it work. No prompt text is stored."""
    __tablename__ = "ai_usage"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)    # ok | invalid | timeout | error | blocked_budget | blocked_cap | disabled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class ReminderLog(Base):
    """One reminder decision per task and kind. The unique key stops duplicates; the status is the honest delivery result."""
    __tablename__ = "reminder_log"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)       # lead48 | lead24 | ... | same_day | overdue | test
    dedupe_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)     # sent (handed to the mail server) | outbox (saved as a file, NOT sent) | failed | skipped (superseded by a closer reminder)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    detail: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_reminder_dedupe"),)


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    stats: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    text: Mapped[str] = mapped_column(String(3000), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_review_week"),)
