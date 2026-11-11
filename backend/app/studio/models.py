"""Tables of the Learning Studio. A pack is written once (by the AI, or from the built-in sample) and then only read and practised."""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fk_user() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)


class LearningPack(Base):
    """One generated (or sample) pack. The unique (user, content_hash) pair is the duplicate-generation guard: the same text is never paid for twice."""
    __tablename__ = "learning_packs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = _fk_user()
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="ai")          # ai | sample
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="generating")  # generating | ready | failed
    error: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    model: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    lessons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    input_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "content_hash", name="uq_pack_user_hash"),)


class PackQuestion(Base):
    __tablename__ = "pack_questions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = _fk_user()
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty: Mapped[str] = mapped_column(String(8), nullable=False)                      # easy | medium | hard
    lesson: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)                   # index into the pack's lessons
    question: Mapped[str] = mapped_column(String(400), nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)                             # exactly four texts
    answer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(String(600), nullable=False, default="")
    __table_args__ = (CheckConstraint("answer_index BETWEEN 0 AND 3", name="ck_packq_answer"),)


class PackCard(Base):
    """A flashcard and its spaced-repetition state (box 0 = new, 5 = well known)."""
    __tablename__ = "pack_cards"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = _fk_user()
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lesson: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    front: Mapped[str] = mapped_column(String(300), nullable=False)
    back: Mapped[str] = mapped_column(String(600), nullable=False)
    box: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_rating: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (CheckConstraint("box BETWEEN 0 AND 5", name="ck_packcard_box"),)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = _fk_user()
    difficulty: Mapped[str] = mapped_column(String(8), nullable=False, default="mixed")
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, nullable=False)
    answers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)               # [{question_id, chosen, correct}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
