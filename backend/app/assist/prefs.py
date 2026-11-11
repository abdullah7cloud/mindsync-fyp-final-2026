"""GET/PUT /settings and /profile for signed-in students. Partial updates are merged onto what is stored, then fully validated."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import service as ai
from app.auth import get_current_user
from app.database import get_db
from app.models import User, UserSkill
from app.notifier import delivery_mode
from app.taskaware import history as H
from app.taskaware.routes import learned_summary

from . import store
from .models import UserProfile, UserSettings
from .settings_schema import LEAD_CHOICES, StudyProfile, StudySettings

router = APIRouter(tags=["settings and profile"])


def _merge(current: dict, patch: dict, model) -> dict:
    if not isinstance(patch, dict) or len(patch) > 40:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Send an object of settings to change.")
    merged = {**current, **patch}
    try:
        return model(**merged).model_dump()
    except ValidationError as e:
        msgs = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()][:5]
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "; ".join(msgs))


@router.get("/settings")
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    st = await store.get_settings(db, user.id)
    d = st.model_dump()
    d["remind_enabled"] = bool(user.email_alerts) and d["remind_enabled"]
    return {"settings": d, "lead_choices": list(LEAD_CHOICES), "delivery_mode": delivery_mode(), "email": user.email,
            "ai": await ai.status(ai.AICtx(db=db, user_id=user.id, student_allows=st.ai_assist))}


@router.put("/settings")
async def put_settings(patch: dict[str, Any], user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    current = (await store.get_settings(db, user.id)).model_dump()
    new = _merge(current, patch, StudySettings)
    row = await db.get(UserSettings, user.id)
    if row is None:
        db.add(UserSettings(user_id=user.id, data=new))
    else:
        row.data = new
    user.email_alerts = bool(new["remind_enabled"])            # the one master switch the reminder job already honours
    await db.commit()
    changed = sorted(k for k in new if new[k] != current.get(k))
    return {"settings": new, "changed": changed}


@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    prof = await store.get_profile(db, user.id)
    skills = {s.kind: s.level for s in (await db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))).all()}
    core = await store.load_core(db, user)
    learned = learned_summary(skills, core.outcomes, core.sessions)
    return {"account": {"display_name": user.display_name, "email": user.email, "member_since": user.created_at.isoformat()},
            "profile": prof.model_dump(), "skills": skills, "learned": learned}


@router.put("/profile")
async def put_profile(patch: dict[str, Any], user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    patch = dict(patch)
    name = patch.pop("display_name", None)
    if name is not None:
        name = " ".join(str(name).split())
        if not 1 <= len(name) <= 100:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Your name must be 1 to 100 characters.")
        user.display_name = name
    current = (await store.get_profile(db, user.id)).model_dump()
    new = _merge(current, patch, StudyProfile)
    row = await db.get(UserProfile, user.id)
    if row is None:
        db.add(UserProfile(user_id=user.id, data=new))
    else:
        row.data = new
    await db.commit()
    return {"profile": new, "display_name": user.display_name}
