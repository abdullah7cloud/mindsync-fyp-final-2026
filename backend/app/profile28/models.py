"""Tables of Update 28 (My Profile and Settings). They are NEW tables: no existing table is changed, so an existing database keeps working."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fk_user(primary: bool = False) -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=primary, nullable=False, index=not primary)


class ProfilePicture(Base):
    """The student's profile picture. Stored already re-drawn by the server as a small square image (no hidden camera data)."""
    __tablename__ = "u28_pictures"
    user_id: Mapped[uuid.UUID] = _fk_user(primary=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mime: Mapped[str] = mapped_column(String(20), nullable=False, default="image/jpeg")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)          # changes with every new picture, so the browser refreshes it
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Preferences(Base):
    """Settings page: e-mail reminders and time zone. Reminders are OFF until the student switches them on."""
    __tablename__ = "u28_preferences"
    user_id: Mapped[uuid.UUID] = _fk_user(primary=True)
    remind_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remind_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=30)    # 30 or 35 (percent of the time that is still left)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class EmailChange(Base):
    """A pending change of the sign-in e-mail. Only a keyed hash of the 6-digit code is kept, never the code itself."""
    __tablename__ = "u28_email_changes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    new_email: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class TaskReminder(Base):
    """One row per task and due date. The unique key is what makes a duplicate e-mail impossible, even with two schedulers running."""
    __tablename__ = "u28_task_reminders"
    __table_args__ = (UniqueConstraint("task_id", "due_key", name="uq_u28_reminder_task_due"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)    # no foreign key: the record stays correct if the task is deleted
    due_key: Mapped[str] = mapped_column(String(10), nullable=False)                               # the task's due date, YYYY-MM-DD
    percent: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="claiming")           # claiming | sent | outbox | failed | skipped
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    detail: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
