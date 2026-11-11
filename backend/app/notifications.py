"""Routes for the email deadline-alert feature (settings, test email, run-now)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.assist import store as assist_store
from app.assist.models import ReminderLog, UserSettings
from app.models import User
from app.notifier import build_test_email, classify_mail_error, deliver, delivery_mode, run_reminder_cycle
from app.ratelimit import LoginRateLimiter

log = logging.getLogger("mindsync.notifications")
router = APIRouter(prefix="/notifications", tags=["notifications"])

# A person can send themselves at most 5 emails per 10 minutes (stops the test
# button being used to spam an address or burn the mail quota).
mail_limiter = LoginRateLimiter(max_failures=5, window_seconds=600)


class AlertStatus(BaseModel):
    email_alerts: bool
    hours_before: int
    delivery_mode: str          # "smtp" = real emails, "outbox" = saved as files (no mail server set)
    email: str
    lead_hours: list[int] = []
    same_day: bool = False
    overdue: bool = False
    timezone: str = "UTC"
    delivery_note: str = ""


class AlertSettingsUpdate(BaseModel):
    email_alerts: bool


class RunResult(BaseModel):
    emails: int
    tasks: int
    failures: int
    mode: str
    skipped: int = 0


NOTE = {"smtp": "A mail server is set up. “Sent” means the server accepted the message; it cannot prove the message reached your inbox.",
        "outbox": "No mail server is set up on this computer, so reminders are only saved as files. Nothing is emailed."}


async def _status(user: User, db: AsyncSession) -> AlertStatus:
    st = await assist_store.get_settings(db, user.id)
    return AlertStatus(
        email_alerts=user.email_alerts,
        hours_before=max(st.remind_lead_hours) if st.remind_lead_hours else settings.reminder_hours_before,
        delivery_mode=delivery_mode(),
        email=user.email,
        lead_hours=st.remind_lead_hours, same_day=st.same_day_reminder, overdue=st.overdue_reminder, timezone=st.timezone,
        delivery_note=NOTE[delivery_mode()],
    )


def _check_rate(user: User) -> None:
    key = str(user.id)
    wait = mail_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many emails requested. Try again in a few minutes.",
                            headers={"Retry-After": str(wait)})
    mail_limiter.record_failure(key)


@router.get("/status", response_model=AlertStatus)
async def alert_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> AlertStatus:
    return await _status(current_user, db)


@router.patch("/settings", response_model=AlertStatus)
async def update_settings(payload: AlertSettingsUpdate, current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)) -> AlertStatus:
    current_user.email_alerts = payload.email_alerts
    row = await db.get(UserSettings, current_user.id)           # keep the new Settings page and this older switch in step
    if row is not None:
        row.data = {**row.data, "remind_enabled": payload.email_alerts}
    await db.commit()
    await db.refresh(current_user)
    return await _status(current_user, db)


@router.post("/test")
async def send_test(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _check_rate(current_user)
    import uuid
    try:
        mode = await deliver(build_test_email(current_user))
    except Exception as exc:
        code, hint = classify_mail_error(exc)   # fixed, plain-English hint; the raw error text is never shown or logged
        log.warning("Test email failed (%s, %s)", code, type(exc).__name__)
        db.add(ReminderLog(user_id=current_user.id, kind="test", dedupe_key=f"test:{uuid.uuid4().hex}", status="failed", detail=f"error: {code}"))
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, hint)
    db.add(ReminderLog(user_id=current_user.id, kind="test", dedupe_key=f"test:{uuid.uuid4().hex}", status="sent" if mode == "smtp" else "outbox",
                       detail="accepted by the mail server" if mode == "smtp" else "saved as a file; no mail server is set up"))
    await db.commit()
    if mode == "outbox":
        return {"mode": mode, "message": "No mail server is set up, so the test email was saved in backend/outbox instead. "
                                         "See docs/EMAIL_ALERTS.md (or run test-email.bat) to switch on real email."}
    return {"mode": mode, "message": f"The mail server accepted a test email for {current_user.email}. Check your inbox (and spam folder) to confirm it arrived."}


@router.post("/check-now", response_model=RunResult)
async def check_now(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> RunResult:
    """Runs the deadline check for the signed-in user right now (also what the background job does)."""
    _check_rate(current_user)
    result = await run_reminder_cycle(db, only_user=current_user.id)
    return RunResult(**result)
