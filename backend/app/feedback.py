"""
"Was this recommendation helpful?" - feedback routes.

POST /feedback          store one yes/no answer plus the situation numbers (energy, difficulty, hours left)
GET  /feedback/summary  how often the recommendations were found helpful (for the progress panel)

This is the project's real-world evaluation hook: it measures whether recommendations are useful to actual
students, and it records labelled examples a future model could be retrained on. No task text is stored.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import RecommendationFeedback, User
from app.ratelimit import LoginRateLimiter
from app.schemas import FeedbackCreate, FeedbackSummary

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Stops someone from filling the table: 60 answers per user per hour is far more than real use.
feedback_limiter = LoginRateLimiter(60, 3600)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_feedback(payload: FeedbackCreate, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)) -> dict:
    key = str(user.id)
    wait = feedback_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many feedback answers. Try again later.",
                            headers={"Retry-After": str(wait)})
    feedback_limiter.record_failure(key)   # (the limiter class counts every call, not only failures)
    db.add(RecommendationFeedback(user_id=user.id, **payload.model_dump()))
    await db.commit()
    return {"saved": True}


@router.get("/summary", response_model=FeedbackSummary)
async def feedback_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> FeedbackSummary:
    total, helpful = (await db.execute(
        select(func.count(RecommendationFeedback.id),
               func.coalesce(func.sum(case((RecommendationFeedback.helpful.is_(True), 1), else_=0)), 0))
        .where(RecommendationFeedback.user_id == user.id))).one()
    total, helpful = int(total), int(helpful)
    return FeedbackSummary(total=total, helpful=helpful,
                           helpful_percent=round(100 * helpful / total, 1) if total else None)
