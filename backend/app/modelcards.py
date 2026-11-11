"""
Public "model cards": which locally trained models are running, what they were trained on and how
they scored on data they had never seen. The dashboard shows this in its "How the models work" panel
so a student (or a professor) can see the evidence instead of just trusting the word "AI".
"""
from fastapi import APIRouter

from app.config import settings
from app.ai import service as ai_service
from app.ai.provider import OpenAIProvider
from app.ml import predictor, wellbeing_model

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status")
async def models_status() -> dict:
    tf = predictor.MODEL
    wb = wellbeing_model.MODEL
    # True only when an OpenAI key is configured here. Without one, every sentence comes from MindSync's own rules.
    external = isinstance(ai_service.current_provider(), OpenAIProvider)
    return {
        "external_ai_used": external,
        "external_ai_note": ("An external language model is configured. It only reads what you type and writes explanations; it never schedules, ranks "
                             "or scores anything, and it is skipped whenever you switch the AI assistant off in Settings.") if external else
                            "No external language model is configured, so everything is produced by MindSync's own rules and locally trained models.",
        "task_fit": None if tf is None else {
            "kind": tf.kind, "version": tf.version, "trained_on": tf.trained_on, "evaluation": tf.evaluation,
            # Experimental: trained on simulated data, so it only affects the ranking if switched on (ML_ENABLED).
            "used_in_ranking": bool(settings.ml_enabled),
            "purpose": "Experimental. Estimates the chance a task is a good fit right now. "
                       + (f"Currently blended {round(settings.ml_weight * 100)}% into the ranking."
                          if settings.ml_enabled else "Currently NOT used: the ranking is the transparent formula only."),
        },
        "wellbeing": None if wb is None else {
            "kind": wb.kind, "version": wb.version, "trained_on": wb.trained_on, "evaluation": wb.metrics,
            "limitations": wb.card.get("limitations", []),
            "purpose": "Estimates the stress level (Low / Medium / High) that a survey dataset's scoring rule gives to your answers. It does not predict burnout and is not a diagnosis.",
        },
    }
