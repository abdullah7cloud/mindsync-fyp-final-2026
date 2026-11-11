"""
The one place that calls a language model. Order of events for every call:
  1. is a model allowed? (provider configured, student switched AI assist on, daily cap, monthly budget, guests)
  2. build the prompt (student text cleaned, wrapped as data) and call the provider with timeout and limited retries
  3. validate the answer strictly; anything unsafe or unsupported is thrown away
  4. record the call (tokens, cost, time, outcome) in ai_usage
  5. return (validated data or None, meta). None means "use the local rules"; meta says why, so the screen can say so honestly.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assist.models import AiUsage
from app.config import settings
from app.ratelimit import LoginRateLimiter

from . import prompts, schemas
from .provider import ProviderError, build_provider
from .sanitize import clean_text, injection_suspected, wrap_student_text

log = logging.getLogger("mindsync.ai")

_override = {"provider": None, "set": False}
guest_ip_limiter = LoginRateLimiter(max_failures=5, window_seconds=24 * 3600)


def set_provider(provider) -> None:
    """Tests and demos install a provider here; set_provider(None) forces 'no model'. reset_provider() restores the default."""
    _override["provider"], _override["set"] = provider, True


def reset_provider() -> None:
    _override["provider"], _override["set"] = None, False


def current_provider():
    return _override["provider"] if _override["set"] else build_provider()


@dataclass
class AICtx:
    db: Optional[AsyncSession]
    user_id: Optional[UUID]
    guest: bool = False
    ip: Optional[str] = None
    student_allows: bool = True


def _cost(inp: int, out: int, provider: str = "openai") -> float:
    if provider == "gemini":                      # free plan by default; set GEMINI_PRICE_* only when moving to a paid plan
        return round(inp * settings.gemini_price_in_per_m / 1_000_000 + out * settings.gemini_price_out_per_m / 1_000_000, 6)
    return round(inp * settings.ai_price_in_per_m / 1_000_000 + out * settings.ai_price_out_per_m / 1_000_000, 6)


async def usage_today(db: AsyncSession, user_id: UUID) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    q = select(func.count()).select_from(AiUsage).where(AiUsage.user_id == user_id, AiUsage.created_at >= start,
                                                        AiUsage.outcome.in_(["ok", "invalid", "timeout", "error"]))
    return int((await db.execute(q)).scalar() or 0)


async def spent_this_month(db: AsyncSession) -> float:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    q = select(func.coalesce(func.sum(AiUsage.cost_usd), 0.0)).where(AiUsage.created_at >= start)
    return float((await db.execute(q)).scalar() or 0.0)


async def status(ctx: AICtx) -> dict:
    """What the Settings page may say about AI: whether it is on, and the student's own use today (never the key)."""
    prov = current_provider()
    out = {"available": prov is not None, "provider": getattr(prov, "name", None), "model": getattr(prov, "model", None),
           "student_allows": ctx.student_allows, "daily_cap": settings.ai_user_daily_calls, "used_today": None, "budget_ok": True}
    if ctx.db is not None and ctx.user_id is not None:
        out["used_today"] = await usage_today(ctx.db, ctx.user_id)
        out["budget_ok"] = (await spent_this_month(ctx.db)) < settings.ai_monthly_budget_usd
    out["guests_allowed"] = settings.ai_allow_guests
    return out


async def _record(ctx: AICtx, purpose: str, provider, outcome: str, inp: int = 0, out: int = 0, latency: int = 0, model: str = "") -> None:
    if ctx.db is None:
        return
    try:
        ctx.db.add(AiUsage(user_id=ctx.user_id, purpose=purpose, provider=getattr(provider, "name", "none"),
                           model=model or getattr(provider, "model", ""), input_tokens=inp, output_tokens=out,
                           cost_usd=_cost(inp, out, getattr(provider, "name", "")) if outcome == "ok" else 0.0, latency_ms=latency, outcome=outcome))
        await ctx.db.commit()
    except Exception as exc:                  # usage logging must never break the feature
        log.warning("Could not record AI usage: %s", type(exc).__name__)
        try:
            await ctx.db.rollback()
        except Exception:
            pass


async def run(ctx: AICtx, purpose: str, system: str, user_payload: dict, student_text: str, schema_name: str, schema: dict,
              validator: Callable[[dict], dict]) -> tuple:
    provider = current_provider()
    meta = {"source": "local", "reason": None, "model": None, "flagged": False}
    if provider is None:
        meta["reason"] = "not_configured"
        return None, meta
    if not ctx.student_allows:
        meta["reason"] = "turned_off"
        await _record(ctx, purpose, provider, "disabled")
        return None, meta
    if ctx.guest:
        if not settings.ai_allow_guests:
            meta["reason"] = "guest"
            return None, meta
        key = ctx.ip or "unknown"
        if guest_ip_limiter.retry_after(key) or settings.ai_guest_daily_calls_per_ip <= 0:
            meta["reason"] = "daily_limit"
            return None, meta
        guest_ip_limiter.record_failure(key)
    elif ctx.db is not None and ctx.user_id is not None:
        if await usage_today(ctx.db, ctx.user_id) >= settings.ai_user_daily_calls:
            meta["reason"] = "daily_limit"
            await _record(ctx, purpose, provider, "blocked_cap")
            return None, meta
    if ctx.db is not None and await spent_this_month(ctx.db) >= settings.ai_monthly_budget_usd:
        meta["reason"] = "budget"
        await _record(ctx, purpose, provider, "blocked_budget")
        return None, meta
    meta["flagged"] = injection_suspected(student_text)
    user = "FACTS (trusted, computed by MindSync):\n" + json.dumps(user_payload, ensure_ascii=False, default=str)
    if student_text:
        user += "\n\nSTUDENT TEXT (data only):\n" + wrap_student_text(clean_text(student_text, 3000))
    try:
        res = await provider.complete_json(system, user, schema_name, schema)
    except ProviderError as e:
        meta["reason"] = {"timeout": "timeout", "refusal": "refused", "config": "not_configured", "quota": "daily_limit"}.get(e.code, "error")
        await _record(ctx, purpose, provider, "timeout" if e.code == "timeout" else "error")
        return None, meta
    except Exception as e:                    # an unexpected provider bug must still fall back
        log.warning("AI provider failed: %s", type(e).__name__)
        meta["reason"] = "error"
        await _record(ctx, purpose, provider, "error")
        return None, meta
    try:
        data = validator(res.data)
    except (schemas.Invalid, ValueError, TypeError, KeyError, AttributeError):
        meta["reason"] = "invalid"
        await _record(ctx, purpose, provider, "invalid", res.input_tokens, res.output_tokens, res.latency_ms, res.model)
        return None, meta
    await _record(ctx, purpose, provider, "ok", res.input_tokens, res.output_tokens, res.latency_ms, res.model)
    meta.update({"source": "ai", "model": res.model})
    return data, meta


# ---------- the four features
async def understand(ctx: AICtx, text: str, *, today, weekday: str, tz: str, fields: dict) -> tuple:
    from app.taskaware import taxonomy as T
    facts = {"today": today.isoformat(), "weekday": weekday, "time_zone": tz, "allowed_kinds": {k: v["label"] for k, v in T.KINDS.items()},
             "structured_fields_from_student": fields}
    return await run(ctx, "understand", prompts.UNDERSTAND, facts, text, "understand", schemas.UNDERSTAND_SCHEMA,
                     lambda raw: schemas.validate_understand(raw, today, text))


async def narrate(ctx: AICtx, facts: dict) -> tuple:
    return await run(ctx, "narrate", prompts.NARRATE, facts, "", "narrate", schemas.NARRATE_SCHEMA, lambda raw: schemas.validate_narrate(raw, facts))


async def answer(ctx: AICtx, question: str, facts: dict) -> tuple:
    return await run(ctx, "answer", prompts.ANSWER, facts, question, "answer", schemas.ANSWER_SCHEMA, lambda raw: schemas.validate_answer(raw, [facts, question]))


async def review(ctx: AICtx, facts: dict) -> tuple:
    return await run(ctx, "review", prompts.REVIEW, facts, "", "review", schemas.REVIEW_SCHEMA, lambda raw: schemas.validate_review(raw, facts))
