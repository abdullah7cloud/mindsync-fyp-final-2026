"""
My Profile and Settings (Update 28). Every route works only on the logged-in student's own data.

  GET/PUT  /my/profile            name, e-mail, whether there is a picture, a pending e-mail change
  POST     /my/email/start        ask to change the sign-in e-mail (password needed) -> a 6-digit code is e-mailed to the NEW address
  POST     /my/email/confirm      type the code -> the e-mail changes; a notice goes to the OLD address
  POST     /my/email/cancel       drop the pending change
  GET/POST/DELETE /my/avatar      the profile picture (JPEG, PNG or WebP up to 3 MB; the server re-draws it as a small square JPEG)
  GET/PUT  /my/settings           e-mail reminders (on/off, 30 or 35 percent) and time zone
  POST     /my/settings/test-email  send a test reminder to the student's own address
The password is changed with the existing POST /account/password.
"""
import hashlib
import hmac
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import notifier
from app.ai.sanitize import clean_text
from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import PasswordResetToken, User
from app.ratelimit import LoginRateLimiter, limiter_key, login_limiter
from app.security import verify_password_async

from .mail import build_email_changed_notice, build_email_code, build_reminder_test
from .models import EmailChange, Preferences, ProfilePicture
from .reminders import clean_percent

router = APIRouter(prefix="/my", tags=["my profile and settings"])

CODE_MINUTES = 15
MAX_CODE_TRIES = 5
MAX_CODES_PER_HOUR = 3
MAX_PICTURE_BYTES = 3 * 1024 * 1024
PICTURE_SIDE = 256
_picture_limit = LoginRateLimiter(10, 3600)
_test_mail_limit = LoginRateLimiter(3, 3600)
_code_limit = LoginRateLimiter(MAX_CODES_PER_HOUR, 3600)      # counts every request for a code, whether or not the address could be used


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _delivery() -> str:
    return "email" if notifier.delivery_mode() == "smtp" else "demo"


def _hash_code(user_id, new_email: str, code: str) -> str:
    key = settings.jwt_secret.encode()
    return hmac.new(key, f"{user_id}:{new_email.lower()}:{code}".encode(), hashlib.sha256).hexdigest()


async def _prefs(db: AsyncSession, user_id) -> Optional[Preferences]:
    return await db.get(Preferences, user_id)


# ---------------------------------------------------------------- profile
class NameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = " ".join(clean_text(v, 100).split())
        if not v:
            raise ValueError("Your name cannot be empty")
        return v


async def _profile_out(db: AsyncSession, user: User) -> dict:
    pic = await db.get(ProfilePicture, user.id)
    pend = await db.scalar(select(EmailChange).where(EmailChange.user_id == user.id).order_by(EmailChange.created_at.desc()).limit(1))
    pending = None
    if pend is not None and _aware(pend.expires_at) > datetime.now(timezone.utc):
        pending = {"email": pend.new_email, "expires_at": _aware(pend.expires_at).isoformat()}
    return {"display_name": user.display_name, "email": user.email, "member_since": _aware(user.created_at).isoformat(),
            "has_picture": pic is not None, "picture_version": pic.version if pic else 0, "pending_email": pending}


@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return await _profile_out(db, user)


@router.put("/profile")
async def put_profile(body: NameIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    user.display_name = body.display_name
    await db.commit()
    return await _profile_out(db, user)


# ---------------------------------------------------------------- e-mail change with a code
class EmailStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class EmailConfirmIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("/email/start")
async def email_start(body: EmailStartIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    key = limiter_key(user.email, "profile")
    wait = login_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many wrong passwords. Try again later.", headers={"Retry-After": str(wait)})
    if not await verify_password_async(body.password, user.password_hash):
        login_limiter.record_failure(key)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your password is not correct.")
    new = str(body.new_email).strip()
    if new.lower() == user.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That is already your e-mail address.")
    wait = _code_limit.retry_after(str(user.id))
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You asked for several codes. Please wait a little before asking again.", headers={"Retry-After": str(wait)})
    _code_limit.record_failure(str(user.id))
    generic = {"message": f"If this address can be used, we sent a 6-digit code to it. It works for {CODE_MINUTES} minutes.", "delivery": _delivery()}
    taken = await db.scalar(select(User.id).where(func.lower(User.email) == new.lower(), User.id != user.id))
    await db.execute(delete(EmailChange).where(EmailChange.user_id == user.id))          # only one pending change at a time
    if taken is not None:
        await db.commit()                                                                  # same answer as a success: the form never tells who has an account
        return generic
    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.add(EmailChange(user_id=user.id, new_email=new, code_hash=_hash_code(user.id, new, code), attempts=0,
                       expires_at=datetime.now(timezone.utc) + timedelta(minutes=CODE_MINUTES)))
    await db.commit()
    try:
        await notifier.deliver(build_email_code(new, user.display_name, code, CODE_MINUTES))
    except Exception as exc:  # noqa: BLE001
        notifier.log.warning("Could not send the e-mail change code: %s", notifier.classify_mail_error(exc)[0])
        await db.execute(delete(EmailChange).where(EmailChange.user_id == user.id))
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "We could not send the e-mail. Please check the address and try again later.")
    login_limiter.reset(key)
    return generic


@router.post("/email/confirm")
async def email_confirm(body: EmailConfirmIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.scalar(select(EmailChange).where(EmailChange.user_id == user.id).order_by(EmailChange.created_at.desc()).limit(1))
    if row is None or _aware(row.expires_at) <= datetime.now(timezone.utc):
        if row is not None:
            await db.delete(row)
            await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "There is no code waiting, or it has run out. Please ask for a new code.")
    if row.attempts >= MAX_CODE_TRIES:
        await db.delete(row)
        await db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many wrong codes. Please ask for a new code.")
    row.attempts += 1
    if not hmac.compare_digest(row.code_hash, _hash_code(user.id, row.new_email, body.code)):
        left = MAX_CODE_TRIES - row.attempts
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"That code is not right. You have {left} tr{'y' if left == 1 else 'ies'} left." if left > 0 else "That code is not right. Please ask for a new code.")
    taken = await db.scalar(select(User.id).where(func.lower(User.email) == row.new_email.lower(), User.id != user.id))
    if taken is not None:
        await db.delete(row)
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "That e-mail address cannot be used. Please choose another one.")
    old, new = user.email, row.new_email
    user.email = new
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))   # reset links meant for the old address stop working
    await db.execute(delete(EmailChange).where(EmailChange.user_id == user.id))
    await db.commit()
    await notifier.deliver_quietly(build_email_changed_notice(old, user.display_name, new), "e-mail changed notice")
    return {"message": "Your sign-in e-mail was changed.", "profile": await _profile_out(db, user)}


@router.post("/email/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def email_cancel(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    await db.execute(delete(EmailChange).where(EmailChange.user_id == user.id))
    await db.commit()


# ---------------------------------------------------------------- profile picture
def _redraw(data: bytes) -> bytes:
    """Open the upload, check it is really a JPEG/PNG/WebP, and draw a fresh 256x256 JPEG. Camera data and anything hidden in the file are dropped."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = 25_000_000
    try:
        probe = Image.open(io.BytesIO(data))
        if probe.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError("format")
        probe.verify()
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im = ImageOps.fit(im, (PICTURE_SIDE, PICTURE_SIDE), method=Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=88, optimize=True)
        return out.getvalue()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError, SyntaxError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That file is not a picture MindSync can use. Please choose a JPEG, PNG or WebP image.")


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    wait = _picture_limit.retry_after(str(user.id))
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You changed your picture many times. Please try again later.", headers={"Retry-After": str(wait)})
    _picture_limit.record_failure(str(user.id))
    data = await file.read(MAX_PICTURE_BYTES + 1)
    if len(data) > MAX_PICTURE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "That picture is bigger than 3 MB. Please choose a smaller one.")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That file is empty.")
    jpeg = _redraw(data)
    row = await db.get(ProfilePicture, user.id)
    if row is None:
        db.add(ProfilePicture(user_id=user.id, data=jpeg, mime="image/jpeg", version=1, updated_at=datetime.now(timezone.utc)))
    else:
        row.data, row.mime, row.version, row.updated_at = jpeg, "image/jpeg", row.version + 1, datetime.now(timezone.utc)
    await db.commit()
    return await _profile_out(db, user)


@router.get("/avatar")
async def get_avatar(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    row = await db.get(ProfilePicture, user.id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile picture")
    return Response(content=row.data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/avatar")
async def delete_avatar(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(delete(ProfilePicture).where(ProfilePicture.user_id == user.id))
    await db.commit()
    return await _profile_out(db, user)


# ---------------------------------------------------------------- settings
class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remind_enabled: Optional[bool] = None
    remind_percent: Optional[Literal[30, 35]] = None
    timezone: Optional[str] = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def _zone(cls, v):
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            raise ValueError("Please choose a time zone from the list")
        return v


def _settings_out(p: Optional[Preferences]) -> dict:
    return {"remind_enabled": bool(p.remind_enabled) if p else False, "remind_percent": clean_percent(p.remind_percent) if p else 30,
            "timezone": p.timezone if p else "UTC", "delivery": _delivery(), "percent_choices": [30, 35]}


@router.get("/settings")
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return _settings_out(await _prefs(db, user.id))


@router.put("/settings")
async def put_settings(body: SettingsIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await _prefs(db, user.id)
    if p is None:
        p = Preferences(user_id=user.id, remind_enabled=False, remind_percent=30, timezone="UTC")
        db.add(p)
    if body.remind_enabled is not None:
        p.remind_enabled = body.remind_enabled
    if body.remind_percent is not None:
        p.remind_percent = body.remind_percent
    if body.timezone is not None:
        p.timezone = body.timezone
    await db.commit()
    return _settings_out(p)


@router.post("/settings/test-email")
async def test_email(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    wait = _test_mail_limit.retry_after(str(user.id))
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You sent several test e-mails. Please try again later.", headers={"Retry-After": str(wait)})
    _test_mail_limit.record_failure(str(user.id))
    p = await _prefs(db, user.id)
    st = _settings_out(p)
    try:
        await notifier.deliver(build_reminder_test(user.email, user.display_name, st["remind_percent"], st["timezone"]))
    except Exception as exc:  # noqa: BLE001
        notifier.log.warning("Could not send the test e-mail: %s", notifier.classify_mail_error(exc)[0])
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "We could not send the test e-mail. Please check the mail settings of the server.")
    demo = st["delivery"] == "demo"
    return {"delivery": st["delivery"], "message": ("No mail server is set up on this computer, so the test e-mail was saved as a file in backend/outbox instead of being sent."
                                                    if demo else "A test e-mail was sent to your address. It can take a minute to arrive.")}
