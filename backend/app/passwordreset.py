"""
"Forgot password" routes.

  POST /auth/forgot-password  - ask for a reset link by e-mail
  POST /auth/reset-password   - choose a new password with that link

Security design (OWASP A07 Identification and Authentication Failures):
  * The answer to "forgot password" is ALWAYS the same, whether or not the address is registered, so the form cannot
    be used to find out who has an account. The e-mail itself is sent after the answer, so response time does not
    reveal it either (the only difference left is one small database write).
  * The link holds a random 256-bit secret. The database stores only its SHA-256 hash, so a leaked database cannot
    be used to take over accounts. The link works once and expires after RESET_MINUTES.
  * Asking again replaces any earlier unused link. A successful reset removes all of the user's links.
  * Both routes are rate limited (per address+IP and per IP).
  * The new password follows the same rules as sign-up and is hashed with Argon2id on a worker thread.
Limitation (stated in the report): a login token issued BEFORE the reset stays valid until it expires (60 minutes by
default), because tokens are stateless.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import auth
from app.config import settings
from app.database import get_db
from app.models import PasswordResetToken, User
from app.notifier import build_password_changed_email, build_reset_email, deliver_quietly, delivery_mode
from app.ratelimit import LoginRateLimiter, limiter_key
from app.schemas import ForgotPassword, Message, ResetPassword
from app.security import hash_password_async

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_MINUTES = 30

# 5 requests per address+IP per 15 minutes, and 100 per IP per hour (every request counts, valid or not).
forgot_limiter = LoginRateLimiter(max_failures=5, window_seconds=15 * 60)
forgot_ip_limiter = LoginRateLimiter(max_failures=100, window_seconds=60 * 60)
# Wrong or expired links: stops guessing of tokens (which is anyway impractical at 256 bits).
reset_limiter = LoginRateLimiter(max_failures=10, window_seconds=15 * 60)

_GENERIC = "If that address has a MindSync account, we have sent a link to reset the password. It is valid for 30 minutes."


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _too_many(wait: int, text: str) -> HTTPException:
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, text, headers={"Retry-After": str(wait)})


@router.post("/forgot-password", response_model=Message)
async def forgot_password(payload: ForgotPassword, request: Request, background: BackgroundTasks,
                          db: AsyncSession = Depends(get_db)) -> Message:
    ip = request.client.host if request.client else "unknown"
    key = limiter_key(payload.email, ip)
    wait = max(forgot_limiter.retry_after(key), forgot_ip_limiter.retry_after(ip))
    if wait:
        raise _too_many(wait, "Too many password-reset requests. Please try again later.")
    forgot_limiter.record_failure(key)
    forgot_ip_limiter.record_failure(ip)

    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is not None:
        # a new request replaces any earlier unused link
        await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
        secret = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(secret),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_MINUTES),
        ))
        await db.commit()
        link = f"{settings.app_url.rstrip('/')}/reset-password?token={secret}"
        background.add_task(deliver_quietly, build_reset_email(user, link, RESET_MINUTES), "password reset")

    return Message(message=_GENERIC, delivery="email" if delivery_mode() == "smtp" else "demo")


@router.post("/reset-password", response_model=Message)
async def reset_password(payload: ResetPassword, request: Request, background: BackgroundTasks,
                         db: AsyncSession = Depends(get_db)) -> Message:
    ip = request.client.host if request.client else "unknown"
    wait = reset_limiter.retry_after(ip)
    if wait:
        raise _too_many(wait, "Too many attempts. Please try again later.")

    invalid = HTTPException(status.HTTP_400_BAD_REQUEST,
                            "This reset link is not valid or has expired. Please ask for a new one.")
    row = await db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(payload.token)))
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or _aware(row.expires_at) < now:
        reset_limiter.record_failure(ip)
        raise invalid
    user = await db.get(User, row.user_id)
    if user is None:
        reset_limiter.record_failure(ip)
        raise invalid

    user.password_hash = await hash_password_async(payload.new_password)
    # the link is spent, and so is every other link this user had
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    await db.commit()
    auth.login_limiter.reset(limiter_key(user.email, ip))      # a locked-out student can log in again with the new password
    background.add_task(deliver_quietly, build_password_changed_email(user), "password changed")
    return Message(message="Your password was changed. You can now log in with it.")
