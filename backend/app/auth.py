"""
Authentication routes: register, login, and the get_current_user dependency
used to protect every other route in the app.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.ratelimit import limiter_key, login_limiter, register_limiter
from app.schemas import Token, UserLogin, UserOut, UserRegister
from app.security import create_access_token, hash_password_async, verify_password_async

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)) -> Token:
    ip_key = request.client.host if request.client else "unknown"
    wait = register_limiter.retry_after(ip_key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-ups from this address. Please try again later.",
            headers={"Retry-After": str(wait)},
        )
    register_limiter.record_failure(ip_key)   # counts every attempt, not only failures

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        # Clear message so the student knows what went wrong. Trade-off: this
        # reveals that the address is registered (account enumeration); it is
        # limited by the per-IP sign-up rate limiter above, and login itself
        # stays generic. Discussed in the report (Limitations).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in instead.",
        )

    user = User(
        email=payload.email,
        password_hash=await hash_password_async(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, request: Request, db: AsyncSession = Depends(get_db)) -> Token:
    key = limiter_key(payload.email, request.client.host if request.client else None)
    wait = login_limiter.retry_after(key)
    if wait:
        # Too many recent failures for this email+IP: refuse BEFORE doing any
        # database or hashing work (also protects the server from being
        # hammered with expensive Argon2 checks).
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": str(wait)},
        )

    user = await db.scalar(select(User).where(User.email == payload.email))

    # Always run a hash verification, even when no user was found, so that
    # login timing does not reveal whether an email exists (timing-attack /
    # enumeration defence).
    dummy_hash = "$argon2id$v=19$m=19456,t=2,p=1$c29tZXNhbHQAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAA"
    ok = await verify_password_async(payload.password, user.password_hash if user else dummy_hash)

    if user is None or not ok:
        login_limiter.record_failure(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    login_limiter.reset(key)
    return Token(access_token=create_access_token(user.id))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: resolves the bearer JWT to a User, or 401s."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    from app.security import decode_access_token  # local import avoids a cycle at module load

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return user


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
