"""
Energy check-in routes. A student logs a 1-5 energy rating whenever they
want; app/recommend.py reads the most recent ones to set the current
energy level and to detect Burnout Mode (see app/heuristic.py).
"""
from sqlalchemy import select
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import EnergyCheckin, User
from app.schemas import EnergyCheckinCreate, EnergyCheckinOut

router = APIRouter(prefix="/energy-checkins", tags=["energy"])


@router.post("", response_model=EnergyCheckinOut, status_code=status.HTTP_201_CREATED)
async def create_checkin(
    payload: EnergyCheckinCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnergyCheckin:
    # One row per check-in (we keep the history so the dashboard can draw a trend and
    # Burnout Mode can look at the last few readings, not just one).
    checkin = EnergyCheckin(user_id=current_user.id, energy_level=payload.energy_level)
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)
    return checkin


@router.get("", response_model=list[EnergyCheckinOut])
async def list_checkins(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EnergyCheckin]:
    result = await db.scalars(
        select(EnergyCheckin)
        .where(EnergyCheckin.user_id == current_user.id)
        .order_by(EnergyCheckin.created_at.desc())
        .limit(20)   # newest first; the dashboard only needs the recent trend
    )
    return list(result.all())
