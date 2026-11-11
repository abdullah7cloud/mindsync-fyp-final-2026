"""
SQLAlchemy ORM models.

Schema mirrors database/schema.sql (the raw DDL/ERD). Database-level
constraints (NOT NULL, CHECK, foreign keys with ON DELETE CASCADE) are
defined here AND in the raw SQL, per the project contract's requirement
for "database constraint validation" as a defence layer independent of
application-level (Pydantic) validation.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, Float, String, Integer, DateTime, ForeignKey, CheckConstraint, Enum as SAEnum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Argon2id hash string (includes salt + params) — never store or log the raw password.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    # Opt-in/out for the "deadline in 2 days" email alert (on by default).
    email_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    tasks: Mapped[list["Task"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    energy_checkins: Mapped[list["EnergyCheckin"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    wellbeing_checks: Mapped[list["WellbeingCheck"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["RecommendationFeedback"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_task_difficulty_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    # 1 (very easy) .. 5 (very hard) — user-assigned, used directly by the heuristic.
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    # Set when the "deadline soon" email for this task has been sent, so it is only sent once.
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    # When the student marked the task done (NULL while pending). Used for the progress charts and
    # "finished before the deadline" statistics. Cleared again if the task is re-opened.
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


    owner: Mapped["User"] = relationship(back_populates="tasks")


class EnergyCheckin(Base):
    """
    A user's self-reported energy level at a point in time. The heuristic
    reads the most recent check-in; a run of low check-ins is what the
    Burnout Mode trigger (Phase 4) watches for.
    """
    __tablename__ = "energy_checkins"
    __table_args__ = (
        CheckConstraint("energy_level BETWEEN 1 AND 5", name="ck_energy_level_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 1 (exhausted) .. 5 (energised)
    energy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="energy_checkins")


class WellbeingCheck(Base):
    """
    One completed "Wellbeing check": the student's questionnaire answers and what the
    trained stress-risk model predicted for them (see app/ml/wellbeing_model.py).

    Why store it: (1) the dashboard can show a trend over time, (2) the recommender
    switches Burnout Mode on when the latest check is recent and High, (3) the exact
    model version is kept so an old result can always be explained.
    """
    __tablename__ = "wellbeing_checks"
    __table_args__ = (
        CheckConstraint("risk_label IN ('Low', 'Medium', 'High')", name="ck_wellbeing_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The questionnaire answers as sent by the student (already validated against the model's schema).
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    risk_label: Mapped[str] = mapped_column(String(10), nullable=False)
    # {"Low": 0.12, "Medium": 0.30, "High": 0.58} - the model's class probabilities.
    probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="wellbeing_checks")


class RecommendationFeedback(Base):
    """
    "Was this recommendation helpful?" answers.

    Why keep them: they are the only REAL evidence of whether the recommendations work. They give
    the project a measurable result (percentage helpful, split by energy level and Burnout Mode) and
    are the labelled data a future version could use to retrain the task-fit model on real behaviour
    instead of simulated data. Only numbers about the situation are stored, never the task text.
    """
    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        CheckConstraint("energy_level BETWEEN 1 AND 5", name="ck_feedback_energy_range"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_feedback_difficulty_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    energy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    hours_left: Mapped[float] = mapped_column(Float, nullable=False)
    burnout_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="feedback")


class PasswordResetToken(Base):
    """
    One "forgot password" request. We store only a SHA-256 hash of the secret in the e-mailed link, never the
    secret itself, so a copy of the database cannot be used to reset anyone's password. A token works once
    (used_at) and only until expires_at.
    """
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class UserSkill(Base):
    """The student's own rating (1-5) of their experience with a kind of work (programming, mathematics ...)."""
    __tablename__ = "user_skills"
    __table_args__ = (CheckConstraint("level BETWEEN 1 AND 5", name="ck_skill_level_range"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class TaskOutcome(Base):
    """
    How long a finished task really took compared with what MindSync estimated. The engine learns from these.
    Only numbers and the kind of work are stored - never the task text.
    """
    __tablename__ = "task_outcomes"
    __table_args__ = (
        CheckConstraint("actual_minutes BETWEEN 1 AND 6000", name="ck_outcome_actual"),
        CheckConstraint("raw_minutes BETWEEN 1 AND 6000", name="ck_outcome_raw"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_minutes: Mapped[int] = mapped_column(Integer, nullable=False)       # the estimate before calibration
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    felt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)     # how hard it felt, 1-5
    predicted_personal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class SessionLog(Base):
    """One study session the student logged: how long, whether it was finished, and (optionally) how focused they were."""
    __tablename__ = "session_logs"
    __table_args__ = (CheckConstraint("minutes BETWEEN 5 AND 600", name="ck_session_minutes"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    focus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
