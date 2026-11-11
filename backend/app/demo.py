"""
Guest ("try it first") mode.

Visitors can use the dashboard without an account. Their tasks and check-ins stay in THEIR
OWN browser; these routes are stateless: the browser sends the data, the server ranks it with
the same heuristic and trained models as the real app, and nothing is stored. To keep their
data (and get email alerts) a guest registers; the app then moves the guest tasks into the
new account.

Abuse protection (no login here, so limits are per IP address): request-size limits
(<= 25 tasks, short text) and 120 calls per 10 minutes.
"""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.ml import wellbeing_model
from app.planner import PlanRequest, PlanResponse, make_plan
from app.ratelimit import LoginRateLimiter
from app.recommend import build_recommendation
from app.schemas import RecommendationOut, TaskOut
from app.taskaware import history as _hist
from app.taskaware.routes import HistoryIn, KindName
from app.wellbeing import AssessIn, AssessOut, run_model, DISCLAIMER

router = APIRouter(prefix="/demo", tags=["demo (guest mode)"])

demo_rank_limiter = LoginRateLimiter(max_failures=600, window_seconds=600)   # a plain calculation; every page view makes one call, and a class may share one IP


def _check(request: Request) -> None:
    """Count this request against the caller's IP address; refuse with 429 when over the limit."""
    key = request.client.host if request.client else "unknown"
    wait = demo_rank_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many requests. Please slow down or create a free account.",
                            headers={"Retry-After": str(wait)})
    demo_rank_limiter.record_failure(key)


class DemoRecommendIn(BaseModel):
    tasks: list[TaskOut] = Field(max_length=60)
    recent_energy: list[int] = Field(default_factory=list, max_length=5)
    # Result of the guest's latest wellbeing check (kept in their browser), if any.
    stress_risk: str | None = Field(default=None, pattern="^(Low|Medium|High)$")
    # The guest's own saved history (kept in their browser) so estimates can learn from it.
    skills: dict[KindName, int] = Field(default_factory=dict)
    history: HistoryIn | None = None


@router.post("/recommend", response_model=RecommendationOut)
async def demo_recommend(payload: DemoRecommendIn, request: Request) -> RecommendationOut:
    _check(request)
    pending = [t for t in payload.tasks if t.status == "pending"]
    clean = [e for e in payload.recent_energy if 1 <= e <= 5]
    energy = clean[-1] if clean else 3
    outcomes = [_hist.Outcome(o.kind, o.raw_minutes, o.actual_minutes, o.felt, o.predicted_personal)
                for o in (payload.history.outcomes if payload.history else [])]
    skills = {k: v for k, v in payload.skills.items() if 1 <= v <= 5}
    return build_recommendation(pending, energy, clean, payload.stress_risk == "High", skills, outcomes)


@router.post("/planner/plan", response_model=PlanResponse)
async def demo_planner(payload: PlanRequest, request: Request) -> PlanResponse:
    """Study Planner for guests: same engine, nothing stored."""
    _check(request)
    return make_plan(payload)


@router.post("/wellbeing/assess", response_model=AssessOut)
async def demo_wellbeing(payload: AssessIn, request: Request) -> AssessOut:
    """Wellbeing check for guests: the model runs, the result is returned, nothing is stored."""
    _check(request)
    result = run_model(payload.answers)
    return AssessOut(model_version=wellbeing_model.MODEL.version, disclaimer=DISCLAIMER,
                     **{k: result[k] for k in ("label", "probabilities", "confidence", "factors_up", "factors_down")})
