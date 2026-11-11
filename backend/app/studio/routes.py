"""
AI Learning Studio API.

  Making a pack (the ONLY place an AI model is ever called):
    POST /studio/extract            read text out of an uploaded file (no AI)
    POST /studio/packs              create a pack from text: checks every limit, calls the AI once, validates, saves
    POST /studio/sample             save the hand-written sample pack for this student (no AI)
  Using a pack (never calls an AI, works offline from the database):
    GET  /studio/packs, GET /studio/packs/{id}, DELETE /studio/packs/{id}?confirm=true
    POST /studio/packs/{id}/quiz            pick questions (answers are not sent yet)
    POST /studio/packs/{id}/quiz/submit     mark on the server, save the attempt, return explanations
    GET  /studio/packs/{id}/cards           flashcards that are due
    POST /studio/cards/{id}/review          easy / okay / difficult -> next review date
    GET  /studio/packs/{id}/progress, GET /studio/summary
  Guests: GET /demo/studio/sample (the sample pack as public data; the browser practises it locally).
"""
import asyncio
import logging
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import service as ai
from app.ai.provider import ProviderError
from app.ai.sanitize import clean_text, injection_suspected
from app.assist import store
from app.assist.models import AiUsage
from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import User
from app.ratelimit import LoginRateLimiter

from . import extract as EX
from . import pack as PK
from . import samplepack as SP
from . import srs
from .models import LearningPack, PackCard, PackQuestion, QuizAttempt

log = logging.getLogger("mindsync.studio")
router = APIRouter(prefix="/studio", tags=["ai learning studio"])
demo_router = APIRouter(prefix="/demo/studio", tags=["ai learning studio (guest)"])

_extract_limit = LoginRateLimiter(max_failures=20, window_seconds=600)
_generate_limit = LoginRateLimiter(max_failures=12, window_seconds=600)      # a second fence in front of the database-based allowances
_practice_limit = LoginRateLimiter(max_failures=600, window_seconds=600)
STALE_AFTER = timedelta(minutes=5)
ATTEMPT_OUTCOMES = ("ok", "invalid", "timeout", "error")


def _rate(limiter: LoginRateLimiter, key: str) -> None:
    wait = limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please wait a moment.", headers={"Retry-After": str(wait)})
    limiter.record_failure(key)


def _fail(code: str, message: str, http: int = status.HTTP_409_CONFLICT, **extra) -> HTTPException:
    return HTTPException(http, detail={"code": code, "message": message, **extra})


def safe_name(name: str) -> str:
    """Only the last part of a file name, as plain text: ../../etc/passwd.txt becomes passwd.txt."""
    return clean_text(name.replace("\\", "/").split("/")[-1], 200)


# ---------------------------------------------------------------- requests
class CreatePackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=200_000)
    title: str = Field(default="", max_length=120)
    source_name: str = Field(default="", max_length=200)
    consent: bool = False

    @field_validator("title", "source_name")
    @classmethod
    def _c(cls, v: str) -> str:
        return safe_name(v) if v and "/" in v.replace("\\", "/") else clean_text(v, 200)


class QuizIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: Literal[5, 10, 15] = 10
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    retry_attempt_id: Optional[uuid.UUID] = None            # "Retry incorrect": only the questions missed in that attempt


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: uuid.UUID
    chosen: int = Field(ge=0, le=3)


class SubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    answers: list[AnswerIn] = Field(min_length=1, max_length=15)


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: Literal["easy", "okay", "difficult"]


# ---------------------------------------------------------------- helpers
async def _today(db: AsyncSession, user: User) -> date:
    st = await store.get_settings(db, user.id)
    return datetime.now(ZoneInfo(st.timezone)).date()


async def _own_pack(db: AsyncSession, user: User, pack_id: str) -> LearningPack:
    try:
        p = await db.get(LearningPack, uuid.UUID(pack_id))
    except ValueError:
        p = None
    if p is None or p.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Learning pack not found")
    return p


def _is_stale(p: LearningPack) -> bool:
    created = p.created_at if p.created_at.tzinfo else p.created_at.replace(tzinfo=timezone.utc)
    return p.status == "generating" and datetime.now(timezone.utc) - created > STALE_AFTER


async def _counts(db: AsyncSession, pack_id: uuid.UUID) -> dict:
    q = (await db.execute(select(PackQuestion.difficulty, func.count()).where(PackQuestion.pack_id == pack_id).group_by(PackQuestion.difficulty))).all()
    by = {d: n for d, n in q}
    cards = await db.scalar(select(func.count()).select_from(PackCard).where(PackCard.pack_id == pack_id))
    return {"questions": sum(by.values()), "easy": by.get("easy", 0), "medium": by.get("medium", 0), "hard": by.get("hard", 0), "cards": int(cards or 0)}


async def _pack_card(db: AsyncSession, p: LearningPack, today: date, full: bool = False) -> dict:
    out = {"id": str(p.id), "title": p.title, "source": p.source, "source_name": p.source_name, "status": "failed" if _is_stale(p) else p.status,
           "created_at": p.created_at.isoformat(), "provider": p.provider, "model": p.model, "counts": await _counts(db, p.id),
           "ai_made": p.source == "ai", "note": SP.SAMPLE_NOTE if p.source == "sample" else "", "error": p.error}
    due = await db.scalar(select(func.count()).select_from(PackCard).where(PackCard.pack_id == p.id, PackCard.due_on <= today))
    out["cards_due"] = int(due or 0)
    last = await db.scalar(select(QuizAttempt).where(QuizAttempt.pack_id == p.id).order_by(QuizAttempt.created_at.desc()).limit(1))
    out["last_quiz"] = {"correct": last.correct, "total": last.total, "percent": round(100 * last.correct / last.total), "at": last.created_at.isoformat()} if last else None
    if full:
        out["lessons"] = p.lessons
    return out


async def _attempts_count(db: AsyncSession, since: datetime, user_id: Optional[uuid.UUID] = None) -> int:
    q = select(func.count()).select_from(AiUsage).where(AiUsage.purpose == "learning_pack", AiUsage.created_at >= since, AiUsage.outcome.in_(ATTEMPT_OUTCOMES))
    if user_id is not None:
        q = q.where(AiUsage.user_id == user_id)
    return int((await db.execute(q)).scalar() or 0)


def _day_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start() -> datetime:
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------- status and reading files
@router.get("/status")
async def studio_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    st = await store.get_settings(db, user.id)
    lim = PK.limits_for(user)
    prov = ai.current_provider()
    name = getattr(prov, "name", None)
    used_day = await _attempts_count(db, _day_start(), user.id)
    used_month = await _attempts_count(db, _month_start(), user.id)
    packs = int(await db.scalar(select(func.count()).select_from(LearningPack).where(LearningPack.user_id == user.id)) or 0)
    privacy = None
    if name == "gemini":
        privacy = "The text you send is processed by Google Gemini. On Google's free plan the content can be used to improve Google's products, so do not upload private or sensitive material."
    elif name:
        privacy = f"The text you send is processed by the AI provider ({name}). Do not upload private or sensitive material."
    return {"ai_available": prov is not None, "provider": name, "student_allows": st.ai_assist, "limits": lim,
            "used": {"today": used_day, "month": used_month, "packs": packs},
            "remaining_today": max(0, lim["daily_attempts"] - used_day), "remaining_month": max(0, lim["monthly_attempts"] - used_month),
            "file_types": list(EX.ALLOWED), "sample_available": True, "privacy_note": privacy,
            "message": None if prov is not None else "AI is not switched on yet. You can still try the sample pack, and everything you have already saved works as normal."}


@router.post("/extract")
async def extract_text(file: UploadFile = File(...), user: User = Depends(get_current_user)) -> dict:
    _rate(_extract_limit, str(user.id))
    limit = settings.studio_max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)                      # never read more than the limit allows
    try:
        text = await EX.extract(file.filename or "", data)
    except EX.ExtractError as e:
        raise _fail(e.code, e.message, status.HTTP_422_UNPROCESSABLE_ENTITY)
    text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
    text = clean_text(text, 400_000)
    lim = PK.limits_for(user)
    if len(text) < 20:
        raise _fail("no_text", "No readable text was found. Scanned pages and pictures cannot be read. Paste the text instead.", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return {"text": text[:lim["max_chars"] * 3], "chars": len(text), "too_long": len(text) > lim["max_chars"], "max_chars": lim["max_chars"],
            "min_chars": lim["min_chars"], "filename": safe_name(file.filename or "")}


# ---------------------------------------------------------------- saving a pack
async def _save_content(db: AsyncSession, pack: LearningPack, content: dict, today: date) -> None:
    pack.lessons = content["lessons"]
    for i, q in enumerate(content["questions"]):
        db.add(PackQuestion(pack_id=pack.id, user_id=pack.user_id, position=i, difficulty=q["difficulty"], lesson=q["lesson"], question=q["question"],
                            options=q["options"], answer_index=q["answer_index"], explanation=q["explanation"]))
    for i, c in enumerate(content["cards"]):
        db.add(PackCard(pack_id=pack.id, user_id=pack.user_id, position=i, lesson=c.get("lesson"), front=c["front"], back=c["back"], box=0, due_on=today))
    pack.status, pack.error, pack.ready_at = "ready", "", datetime.now(timezone.utc)


@router.post("/sample")
async def add_sample(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """The hand-written sample. Saved like any pack so quizzes, flashcards and progress behave exactly the same. No AI, no allowance used."""
    _rate(_practice_limit, str(user.id))
    h = PK.content_hash("mindsync-sample-pack-v1")
    existing = await db.scalar(select(LearningPack).where(LearningPack.user_id == user.id, LearningPack.content_hash == h))
    today = await _today(db, user)
    if existing is not None:
        return {"reused": True, "pack": await _pack_card(db, existing, today)}
    pack = LearningPack(user_id=user.id, title=SP.SAMPLE_TITLE, source_name="Built-in sample", source="sample", content_hash=h, status="generating",
                        provider="none", model="hand-written")
    db.add(pack)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(select(LearningPack).where(LearningPack.user_id == user.id, LearningPack.content_hash == h))
        return {"reused": True, "pack": await _pack_card(db, existing, today)}
    await _save_content(db, pack, SP.sample_payload(), today)
    await db.commit()
    return {"reused": False, "pack": await _pack_card(db, pack, today)}


@router.post("/packs", status_code=status.HTTP_201_CREATED)
async def create_pack(body: CreatePackIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """The one place the AI is called. Every guard below runs BEFORE any request is sent, so a refused request costs nothing."""
    uid = str(user.id)
    _rate(_generate_limit, uid)
    lim = PK.limits_for(user)
    text = clean_text(body.text, 400_000)
    chars = len(PK.normalise(text))
    if chars < lim["min_chars"]:
        raise _fail("too_short", f"Please give at least {lim['min_chars']} characters of study material.", status.HTTP_422_UNPROCESSABLE_ENTITY)
    if chars > lim["max_chars"]:
        raise _fail("too_long", f"This text has {chars:,} characters. The limit is {lim['max_chars']:,}. Please split it into parts.", status.HTTP_422_UNPROCESSABLE_ENTITY,
                    chars=chars, max_chars=lim["max_chars"])
    today = await _today(db, user)

    # 1. the same material again -> the saved pack, no AI call
    h = PK.content_hash(text)
    existing = await db.scalar(select(LearningPack).where(LearningPack.user_id == user.id, LearningPack.content_hash == h))
    if existing is not None:
        if existing.status == "ready":
            return {"reused": True, "message": "You already made a pack from this material, so it was opened. No AI request was used.", "pack": await _pack_card(db, existing, today)}
        if existing.status == "generating" and not _is_stale(existing):
            raise _fail("in_progress", "This pack is already being created. Please wait a moment.")
        await db.delete(existing)                                  # a failed or abandoned attempt: allow a fresh try (the allowance still counts it)
        await db.flush()

    # 2. is AI on, and is this student allowed?
    prov = ai.current_provider()
    if prov is None:
        raise _fail("ai_not_active", "AI is not switched on yet, so a pack cannot be made from your own material. You can try the sample pack instead.")
    st = await store.get_settings(db, user.id)
    if not st.ai_assist:
        raise _fail("ai_off", "You switched AI help off in Settings. Switch it on there to create a pack.")
    if not body.consent:
        raise _fail("consent", "Please confirm that you agree to send this text to the AI provider.", status.HTTP_422_UNPROCESSABLE_ENTITY)

    # 3. allowances
    ctx = ai.AICtx(db=db, user_id=user.id, student_allows=True)
    packs = int(await db.scalar(select(func.count()).select_from(LearningPack).where(LearningPack.user_id == user.id)) or 0)
    if packs >= lim["max_packs"]:
        raise _fail("too_many_packs", f"You have {packs} packs, which is the limit. Delete one you no longer need.")
    busy = await db.scalar(select(LearningPack).where(LearningPack.user_id == user.id, LearningPack.status == "generating",
                                                      LearningPack.created_at >= datetime.now(timezone.utc) - STALE_AFTER))
    if busy is not None:
        raise _fail("in_progress", "A pack is already being created. Please wait until it finishes.")
    last = await db.scalar(select(func.max(AiUsage.created_at)).where(AiUsage.user_id == user.id, AiUsage.purpose == "learning_pack", AiUsage.outcome.in_(ATTEMPT_OUTCOMES)))
    if last is not None:
        last = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
        wait = int(lim["cooldown_seconds"] - (datetime.now(timezone.utc) - last).total_seconds())
        if wait > 0:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": "cooldown", "message": f"Please wait {wait} seconds before making another pack.", "retry_after": wait},
                                headers={"Retry-After": str(wait)})
    if await _attempts_count(db, _day_start(), user.id) >= lim["daily_attempts"]:
        await ai._record(ctx, "learning_pack", prov, "blocked_cap")
        raise _fail("daily_limit", f"You have used your {lim['daily_attempts']} pack attempts for today. Your saved packs still work. Try again tomorrow.", status.HTTP_429_TOO_MANY_REQUESTS)
    if await _attempts_count(db, _month_start(), user.id) >= lim["monthly_attempts"]:
        await ai._record(ctx, "learning_pack", prov, "blocked_cap")
        raise _fail("monthly_limit", f"You have used your {lim['monthly_attempts']} pack attempts for this month. Your saved packs still work.", status.HTTP_429_TOO_MANY_REQUESTS)
    if await _attempts_count(db, _day_start()) >= settings.studio_global_daily_attempts:
        await ai._record(ctx, "learning_pack", prov, "blocked_cap")
        raise _fail("service_busy", "The AI allowance for everyone is used up for today. Please try again tomorrow. Your saved packs still work.", status.HTTP_429_TOO_MANY_REQUESTS)
    if await ai.spent_this_month(db) >= settings.ai_monthly_budget_usd:
        await ai._record(ctx, "learning_pack", prov, "blocked_budget")
        raise _fail("budget", "The monthly AI budget has been reached, so no new packs can be made until next month. Your saved packs still work.", status.HTTP_429_TOO_MANY_REQUESTS)

    # 4. reserve the row first: a second click, a second tab or a retry cannot start a second generation (unique user + content)
    title = body.title or "Learning pack"
    pack = LearningPack(user_id=user.id, title=title[:120], source_name=body.source_name, source="ai", content_hash=h, status="generating",
                        provider=getattr(prov, "name", "ai"), model=getattr(prov, "model", ""), input_chars=chars)
    db.add(pack)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _fail("in_progress", "This pack is already being created. Please wait a moment.")

    # 5. the single AI call
    flagged = injection_suspected(text)
    try:
        res = await prov.complete_json(PK.PROMPT_SYSTEM, PK.build_user_message(text),
                                       "learning_pack", PK.PACK_SCHEMA, max_tokens=settings.studio_max_output_tokens, timeout=lim["timeout_seconds"])
    except ProviderError as e:
        outcome = "timeout" if e.code == "timeout" else "error"
        msg = {"timeout": "The AI took too long, so it was stopped. Nothing was lost. Please try again in a few minutes.",
               "quota": "The free AI allowance is used up for now. Please try again later. Your saved packs still work.",
               "refusal": "The AI declined to work with this text. Try different material.",
               "config": "AI is not set up correctly on the server."}.get(e.code, "The AI service did not answer. Please try again later.")
        return await _failed(db, pack, ctx, prov, outcome, msg, e.code)
    except asyncio.CancelledError:
        pack.status, pack.error = "failed", "cancelled"
        await db.commit()
        raise
    except Exception as e:
        log.warning("Learning pack generation failed: %s", type(e).__name__)
        return await _failed(db, pack, ctx, prov, "error", "Something went wrong while making the pack. Nothing was lost. Please try again later.", "error")

    # 6. never trust the answer: validate, keep what is good, refuse when too little is left
    try:
        content = PK.validate_pack(res.data, text)
    except Exception:
        await ai._record(ctx, "learning_pack", prov, "invalid", res.input_tokens, res.output_tokens, res.latency_ms, res.model)
        pack.status, pack.error = "failed", "invalid"
        await db.commit()
        raise _fail("invalid", "The AI's answer was not good enough to use, so nothing was saved. Please try again later.", status.HTTP_502_BAD_GATEWAY)
    pack.title = (body.title or content["title"] or "Learning pack")[:120]
    pack.model, pack.input_tokens, pack.output_tokens = res.model, res.input_tokens, res.output_tokens
    await _save_content(db, pack, content, today)
    await db.commit()
    await ai._record(ctx, "learning_pack", prov, "ok", res.input_tokens, res.output_tokens, res.latency_ms, res.model)
    return {"reused": False, "flagged": flagged, "message": "Your learning pack is ready and saved. You can practise it as often as you like without using AI again.",
            "pack": await _pack_card(db, pack, today)}


async def _failed(db: AsyncSession, pack: LearningPack, ctx, prov, outcome: str, message: str, code: str):
    pack.status, pack.error = "failed", code[:200]
    await db.commit()
    await ai._record(ctx, "learning_pack", prov, outcome)
    raise _fail("generation_failed", message, status.HTTP_502_BAD_GATEWAY if code != "quota" else status.HTTP_429_TOO_MANY_REQUESTS, reason=code)


# ---------------------------------------------------------------- reading packs
@router.get("/packs")
async def list_packs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    today = await _today(db, user)
    rows = (await db.scalars(select(LearningPack).where(LearningPack.user_id == user.id).order_by(LearningPack.created_at.desc()))).all()
    return {"packs": [await _pack_card(db, p, today) for p in rows]}


@router.get("/packs/{pack_id}")
async def get_pack(pack_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _own_pack(db, user, pack_id)
    return await _pack_card(db, p, await _today(db, user), full=True)


@router.delete("/packs/{pack_id}")
async def delete_pack(pack_id: str, confirm: bool = Query(default=False), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _own_pack(db, user, pack_id)
    if not confirm:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please confirm that you want to delete this pack and its progress.")
    # Deleting a pack removes its questions, cards and quiz history. It does NOT give back AI allowance (the attempt really happened).
    await db.execute(delete(PackQuestion).where(PackQuestion.pack_id == p.id))
    await db.execute(delete(PackCard).where(PackCard.pack_id == p.id))
    await db.execute(delete(QuizAttempt).where(QuizAttempt.pack_id == p.id))
    await db.delete(p)
    await db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------- quizzes (no AI)
def pick_questions(questions: list, difficulty: str, count: int, rng: random.Random) -> list:
    pool = [q for q in questions if difficulty == "mixed" or q.difficulty == difficulty]
    rng.shuffle(pool)
    if difficulty != "mixed":
        return pool[:count]
    buckets = {d: [q for q in pool if q.difficulty == d] for d in PK.DIFFICULTIES}
    out = []
    while len(out) < count and any(buckets.values()):
        for d in PK.DIFFICULTIES:
            if buckets[d] and len(out) < count:
                out.append(buckets[d].pop())
    rng.shuffle(out)
    return out


@router.post("/packs/{pack_id}/quiz")
async def start_quiz(pack_id: str, body: QuizIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(_practice_limit, str(user.id))
    p = await _own_pack(db, user, pack_id)
    if p.status != "ready":
        raise _fail("not_ready", "This pack is not ready.")
    qs = (await db.scalars(select(PackQuestion).where(PackQuestion.pack_id == p.id).order_by(PackQuestion.position))).all()
    if body.retry_attempt_id:
        at = await db.get(QuizAttempt, body.retry_attempt_id)
        if at is None or at.user_id != user.id or at.pack_id != p.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz attempt not found")
        wrong = {a["question_id"] for a in at.answers if not a["correct"]}
        qs = [q for q in qs if str(q.id) in wrong]
        if not qs:
            raise _fail("nothing_to_retry", "You answered every question correctly in that quiz.")
        chosen = qs
    else:
        chosen = pick_questions(list(qs), body.difficulty, body.count, random.Random())
    if not chosen:
        raise _fail("no_questions", "There are no questions at that difficulty in this pack.")
    titles = {i: l["title"] for i, l in enumerate(p.lessons or [])}
    note = None if len(chosen) >= body.count or body.retry_attempt_id else f"This pack has only {len(chosen)} questions for that choice, so the quiz has {len(chosen)}."
    return {"pack_id": str(p.id), "difficulty": body.difficulty, "total": len(chosen), "note": note,
            "questions": [{"id": str(q.id), "difficulty": q.difficulty, "question": q.question, "options": q.options, "lesson": titles.get(q.lesson)} for q in chosen]}


@router.post("/packs/{pack_id}/quiz/submit")
async def submit_quiz(pack_id: str, body: SubmitIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _own_pack(db, user, pack_id)
    ids = [a.question_id for a in body.answers]
    if len(set(ids)) != len(ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Each question can be answered once.")
    qs = {q.id: q for q in (await db.scalars(select(PackQuestion).where(PackQuestion.pack_id == p.id, PackQuestion.id.in_(ids)))).all()}
    if len(qs) != len(ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Some questions do not belong to this pack.")
    review, stored, correct = [], [], 0
    titles = {i: l["title"] for i, l in enumerate(p.lessons or [])}
    for a in body.answers:
        q = qs[a.question_id]
        ok = a.chosen == q.answer_index
        correct += ok
        stored.append({"question_id": str(q.id), "chosen": a.chosen, "correct": ok})
        review.append({"question_id": str(q.id), "question": q.question, "options": q.options, "chosen": a.chosen, "answer_index": q.answer_index, "correct": ok,
                       "explanation": q.explanation, "difficulty": q.difficulty, "lesson": titles.get(q.lesson)})
    at = QuizAttempt(pack_id=p.id, user_id=user.id, difficulty=body.difficulty, total=len(ids), correct=correct, answers=stored)
    db.add(at)
    await db.commit()
    wrong_lessons = sorted({r["lesson"] for r in review if not r["correct"] and r["lesson"]})
    return {"attempt_id": str(at.id), "total": len(ids), "correct": correct, "percent": round(100 * correct / len(ids)), "review": review,
            "revise": wrong_lessons, "note": "This score shows how you did on these questions. It is not a measure of how well you understand the whole subject."}


# ---------------------------------------------------------------- flashcards (no AI)
@router.get("/packs/{pack_id}/cards")
async def get_cards(pack_id: str, mode: Literal["due", "all"] = "due", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _own_pack(db, user, pack_id)
    today = await _today(db, user)
    q = select(PackCard).where(PackCard.pack_id == p.id)
    if mode == "due":
        q = q.where(PackCard.due_on <= today)
    rows = (await db.scalars(q.order_by(PackCard.due_on, PackCard.position).limit(60))).all()
    total = int(await db.scalar(select(func.count()).select_from(PackCard).where(PackCard.pack_id == p.id)) or 0)
    return {"mode": mode, "today": today.isoformat(), "total": total, "cards": [_card(c) for c in rows]}


def _card(c: PackCard) -> dict:
    return {"id": str(c.id), "front": c.front, "back": c.back, "box": c.box, "due_on": c.due_on.isoformat() if c.due_on else None, "reviews": c.reviews}


@router.post("/cards/{card_id}/review")
async def review_card(card_id: str, body: ReviewIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(_practice_limit, str(user.id))
    try:
        c = await db.get(PackCard, uuid.UUID(card_id))
    except ValueError:
        c = None
    if c is None or c.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flashcard not found")
    today = await _today(db, user)
    box, due, lapsed = srs.next_state(c.box, body.rating, today)
    c.box, c.due_on, c.reviews, c.last_rating, c.last_reviewed_at = box, due, c.reviews + 1, body.rating, datetime.now(timezone.utc)
    c.lapses += 1 if lapsed else 0
    await db.commit()
    days = srs.INTERVAL_DAYS[box]
    return {"card": _card(c), "next_review": "tomorrow" if days == 1 else f"in {days} days", "well_known": box >= srs.WELL_KNOWN_BOX}


# ---------------------------------------------------------------- progress (no AI)
async def progress_for(db: AsyncSession, user: User, p: LearningPack, today: date) -> dict:
    attempts = (await db.scalars(select(QuizAttempt).where(QuizAttempt.pack_id == p.id).order_by(QuizAttempt.created_at.desc()).limit(30))).all()
    by_diff = {}
    for d in (*PK.DIFFICULTIES, "mixed"):
        a = [x for x in attempts if x.difficulty == d]
        if a:
            by_diff[d] = {"attempts": len(a), "best": max(round(100 * x.correct / x.total) for x in a), "average": round(sum(100 * x.correct / x.total for x in a) / len(a)),
                          "latest": round(100 * a[0].correct / a[0].total)}
    cards = (await db.scalars(select(PackCard).where(PackCard.pack_id == p.id))).all()
    boxes = {str(b): sum(1 for c in cards if c.box == b) for b in range(6)}
    upcoming = {}
    for c in cards:
        if c.due_on and c.due_on > today and (c.due_on - today).days <= 14:
            upcoming[c.due_on.isoformat()] = upcoming.get(c.due_on.isoformat(), 0) + 1
    qlesson = {q.id: q.lesson for q in (await db.scalars(select(PackQuestion).where(PackQuestion.pack_id == p.id))).all()}
    wrong = {}
    for at in attempts[:10]:
        for a in at.answers:
            if not a["correct"]:
                les = qlesson.get(uuid.UUID(a["question_id"]))
                if les is not None:
                    wrong[les] = wrong.get(les, 0) + 1
    titles = [l["title"] for l in (p.lessons or [])]
    return {"pack_id": str(p.id), "quizzes_taken": len(attempts), "by_difficulty": by_diff,
            "recent": [{"at": x.created_at.isoformat(), "percent": round(100 * x.correct / x.total), "difficulty": x.difficulty, "correct": x.correct, "total": x.total, "id": str(x.id)} for x in attempts[:10]],
            "cards": {"total": len(cards), "due_today": sum(1 for c in cards if c.due_on and c.due_on <= today), "new": sum(1 for c in cards if c.reviews == 0),
                      "well_known": sum(1 for c in cards if c.box >= srs.WELL_KNOWN_BOX), "boxes": boxes, "upcoming": dict(sorted(upcoming.items()))},
            "weak_lessons": [{"lesson": titles[i], "wrong": n} for i, n in sorted(wrong.items(), key=lambda x: -x[1]) if i < len(titles)][:3],
            "note": "Quiz scores and flashcard ratings show practice, not mastery."}


@router.get("/packs/{pack_id}/progress")
async def pack_progress(pack_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _own_pack(db, user, pack_id)
    return await progress_for(db, user, p, await _today(db, user))


async def summary_for(db: AsyncSession, user: User, today: date) -> dict:
    """Real numbers only, for the Dashboard: nothing here exists until the student has really practised."""
    packs = (await db.scalars(select(LearningPack).where(LearningPack.user_id == user.id, LearningPack.status == "ready"))).all()
    attempts = (await db.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user.id).order_by(QuizAttempt.created_at.desc()).limit(50))).all()
    cards = (await db.scalars(select(PackCard).where(PackCard.user_id == user.id))).all()
    title = {p.id: p.title for p in packs}
    recent = [{"pack": title.get(a.pack_id, "(deleted pack)"), "percent": round(100 * a.correct / a.total), "correct": a.correct, "total": a.total, "at": a.created_at.isoformat(), "difficulty": a.difficulty}
              for a in attempts[:5]]
    return {"packs": len(packs), "quizzes_taken": len(attempts), "average_percent": round(sum(100 * a.correct / a.total for a in attempts[:10]) / len(attempts[:10])) if attempts else None,
            "recent_quizzes": recent, "cards_total": len(cards), "cards_due": sum(1 for c in cards if c.due_on and c.due_on <= today),
            "cards_well_known": sum(1 for c in cards if c.box >= srs.WELL_KNOWN_BOX), "reviews_total": sum(c.reviews for c in cards)}


@router.get("/summary")
async def studio_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return await summary_for(db, user, await _today(db, user))


# ---------------------------------------------------------------- guests
@demo_router.get("/sample")
async def demo_sample(request: Request) -> dict:
    """The hand-written sample as public data. A guest's browser marks quizzes and schedules flashcards itself; nothing is stored here."""
    p = SP.sample_payload()
    return {"title": p["title"], "note": SP.SAMPLE_NOTE, "lessons": p["lessons"], "questions": p["questions"], "cards": p["cards"]}
