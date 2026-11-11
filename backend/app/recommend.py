"""
The /recommend route: ties together the local heuristic (app/heuristic.py), the trained
task-fit model (app/ml), the latest wellbeing-check result (app/wellbeing.py) and the
plain-English explanation (app/explain.py), behind the schema boundary defined in
app/schemas.py (RecommendationOut). Nothing here calls an external service.

`build_recommendation` is a plain function shared by this route (logged-in users, data
from PostgreSQL) and by the guest route in app/demo.py (data sent by the browser), so the
ranking logic exists exactly once.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.explain import explain_recommendation
from app.heuristic import ScorableTask, is_burnout_mode, rank_tasks
from app.ml import predictor
from app.models import EnergyCheckin, Task, TaskOutcome, TaskStatus, User, UserSkill
from app.schemas import RecommendationOut, RecommendedTask, TaskOut
from app.taskaware.ranking import rank_smart
from app.taskaware import history as _hist
from app.wellbeing import latest_recent_label

router = APIRouter(tags=["recommend"])

# How many past energy check-ins to look at for the burnout-mode trigger.
_RECENT_CHECKIN_LOOKBACK = 5
# Neutral default when a student has never logged an energy check-in yet.
_DEFAULT_ENERGY_LEVEL = 3


def build_recommendation(
    pending: list[TaskOut],
    energy: int,
    recent_energy: list[int],
    high_stress: bool,
    skills: dict | None = None,
    outcomes: list | None = None,
) -> RecommendationOut:
    """
    Rank the pending tasks and explain the result.

    pending        - the student's pending tasks
    energy         - latest energy check-in (1-5)
    recent_energy  - last few check-ins, OLDEST first (for the Burnout Mode rule)
    high_stress    - True when the latest wellbeing check predicted a High stress risk
    """
    # Use the trained model only if enabled in settings AND its weights loaded.
    use_ml = settings.ml_enabled and predictor.MODEL is not None

    scorable = [ScorableTask(id=str(t.id), title=t.title, difficulty=t.difficulty, deadline=t.deadline) for t in pending]
    now = datetime.now(timezone.utc)
    if settings.smart_ranking and not use_ml:
        # work-pressure ranking: knows how much work each task needs, not only when it is due
        ranked, burnout_mode = rank_smart(
            scorable, energy, details={str(t.id): (t.description, t.category) for t in pending}, now=now,
            recent_energy=recent_energy, extra_burnout=high_stress, skills=skills, outcomes=outcomes)
    else:
        ranked, burnout_mode = rank_tasks(
            tasks=scorable,
            energy_level=energy,
            recent_energy_levels=recent_energy,
            now=now,
            ml_scorer=predictor.task_fit_scorer if use_ml else None,
            ml_weight=settings.ml_weight if use_ml else 0.0,
            extra_burnout=high_stress,
        )
    burnout_reason = None
    if burnout_mode:
        burnout_reason = "low_energy" if is_burnout_mode(recent_energy) else "high_stress_risk"

    by_id = {str(t.id): t for t in pending}
    ranked_out = [
        RecommendedTask(task=by_id[st.task.id], score=st.score, score_breakdown=st.breakdown) for st in ranked
    ]
    top = ranked_out[0] if ranked_out else None

    explanation = explain_recommendation(
        top_title=top.task.title if top else None,
        top_difficulty=top.task.difficulty if top else None,
        breakdown=top.score_breakdown if top else {},
        energy_level=energy,
        burnout_mode=burnout_mode,
        burnout_reason=burnout_reason,
    )
    return RecommendationOut(
        ranked_tasks=ranked_out,
        top_task=top,
        explanation=explanation,
        explanation_source="local_rules" if top else "no_tasks",
        burnout_mode=burnout_mode,
        burnout_reason=burnout_reason,
        ml_model=predictor.MODEL.kind if use_ml else None,
    )


@router.get("/recommend", response_model=RecommendationOut)
async def recommend(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationOut:
    # Only the logged-in user's own pending tasks (filtering by owner_id is the IDOR defence).
    tasks = await db.scalars(
        select(Task).where(Task.owner_id == current_user.id, Task.status == TaskStatus.pending)
    )
    pending = [TaskOut.model_validate(t) for t in tasks.all()]

    checkins = await db.scalars(
        select(EnergyCheckin)
        .where(EnergyCheckin.user_id == current_user.id)
        .order_by(EnergyCheckin.created_at.desc())
        .limit(_RECENT_CHECKIN_LOOKBACK)
    )
    recent = list(checkins.all())
    energy = recent[0].energy_level if recent else _DEFAULT_ENERGY_LEVEL
    recent_oldest_first = [c.energy_level for c in reversed(recent)]

    high_stress = (await latest_recent_label(db, current_user.id)) == "High"
    skills = {s.kind: s.level for s in (await db.scalars(select(UserSkill).where(UserSkill.user_id == current_user.id))).all()}
    rows = (await db.scalars(select(TaskOutcome).where(TaskOutcome.user_id == current_user.id)
                             .order_by(TaskOutcome.created_at.desc()).limit(200))).all()
    outcomes = [_hist.Outcome(o.kind, o.raw_minutes, o.actual_minutes, o.felt, o.predicted_personal) for o in rows]
    return build_recommendation(pending, energy, recent_oldest_first, high_stress, skills, outcomes)
