"""
Wellbeing check routes: the student answers a short questionnaire and the locally trained
stress-risk model (app/ml/wellbeing_model.py) returns Low / Medium / High with the reasons.

Data flow (one request):
  browser form  ->  POST /wellbeing/assess  ->  validate answers (strict)  ->  model.predict()
      ->  save a row in `wellbeing_checks` (PostgreSQL)  ->  JSON result back to the browser.

Guests use the stateless twin route in app/demo.py (nothing is stored on the server).

IMPORTANT (also shown to the student): this is a study-habit screening aid trained on a
public student survey, NOT a medical or psychological diagnosis.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.ml import wellbeing_model
from app.models import User, WellbeingCheck
from app.ratelimit import LoginRateLimiter

router = APIRouter(prefix="/wellbeing", tags=["wellbeing check"])

# How long a result keeps influencing Burnout Mode / the planner (stress changes over weeks, not months).
RESULT_VALID_DAYS = 14

# Each account may run the check 20 times per hour (stops database spam; normal use is 1-2 a week).
assess_limiter = LoginRateLimiter(max_failures=20, window_seconds=3600)

DISCLAIMER = (
    "This estimate applies the scoring rule of a public student-survey dataset to your answers. It is not a "
    "medical or psychological diagnosis and it does not predict burnout. If you feel unwell or overwhelmed, "
    "please talk to someone you trust, your university's student support or your doctor."
)


class AssessIn(BaseModel):
    # {question name: number or option text}; strictly validated against the model's questionnaire.
    answers: dict[str, Any] = Field(max_length=40)


class Factor(BaseModel):
    feature: str
    label: str
    value: str
    effect: float
    tip: str = ""


class AssessOut(BaseModel):
    label: str
    probabilities: dict[str, float]
    confidence: float
    factors_up: list[Factor]
    factors_down: list[Factor]
    model_version: str
    disclaimer: str = DISCLAIMER
    created_at: Optional[datetime] = None


class HistoryItem(BaseModel):
    label: str
    probabilities: dict[str, float]
    model_version: str
    created_at: datetime


def require_model() -> wellbeing_model.WellbeingModel:
    """The feature is only available once the model has been trained (weights file present)."""
    if wellbeing_model.MODEL is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The wellbeing model has not been trained yet. See docs/WELLBEING_MODEL.md.")
    return wellbeing_model.MODEL


def run_model(answers: dict) -> dict:
    """Validate + predict; turns questionnaire mistakes into a readable HTTP 422."""
    model = require_model()
    try:
        return model.predict(answers)
    except wellbeing_model.AnswerError as exc:
        raise HTTPException(422, str(exc))


@router.get("/model")
async def model_info() -> dict:
    """Public: the questionnaire plus the model card (training data, metrics, limitations)."""
    if wellbeing_model.MODEL is None:
        return {"available": False}
    return {"available": True, **wellbeing_model.MODEL.public_info(), "valid_days": RESULT_VALID_DAYS}


@router.post("/assess", response_model=AssessOut)
async def assess(payload: AssessIn, current_user: User = Depends(get_current_user),
                 db: AsyncSession = Depends(get_db)) -> AssessOut:
    key = str(current_user.id)
    wait = assess_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many checks. Please try again later.",
                            headers={"Retry-After": str(wait)})
    assess_limiter.record_failure(key)

    result = run_model(payload.answers)
    row = WellbeingCheck(user_id=current_user.id, answers=result["answers"], risk_label=result["label"],
                         probabilities=result["probabilities"], model_version=wellbeing_model.MODEL.version)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return AssessOut(model_version=row.model_version, created_at=row.created_at,
                     **{k: result[k] for k in ("label", "probabilities", "confidence", "factors_up", "factors_down")})


@router.get("/history", response_model=list[HistoryItem])
async def history(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(
        select(WellbeingCheck).where(WellbeingCheck.user_id == current_user.id)
        .order_by(WellbeingCheck.created_at.desc()).limit(10)
    )
    return [HistoryItem(label=r.risk_label, probabilities=r.probabilities, model_version=r.model_version,
                        created_at=r.created_at) for r in rows.all()]


async def latest_recent_label(db: AsyncSession, user_id) -> Optional[str]:
    """The user's most recent result if it is still 'fresh' (used by /recommend and the planner)."""
    since = datetime.now(timezone.utc) - timedelta(days=RESULT_VALID_DAYS)
    row = await db.scalar(
        select(WellbeingCheck).where(WellbeingCheck.user_id == user_id, WellbeingCheck.created_at >= since)
        .order_by(WellbeingCheck.created_at.desc()).limit(1)
    )
    return row.risk_label if row else None
