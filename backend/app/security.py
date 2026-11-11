"""
Password hashing and JWT helpers.

Argon2id (via argon2-cffi) is used for password hashing per the project
contract's security requirements — it is the OWASP-recommended default
over bcrypt/PBKDF2 for new applications (resistant to GPU/ASIC cracking
via its memory-hardness). JWTs are signed with HS256 using a server-side
secret (settings.jwt_secret) and carry a short expiry.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

from app.config import settings

# Default argon2-cffi parameters already meet OWASP's minimum recommendation
# (m=19 MiB, t=2, p=1); we keep the library defaults explicit here so a
# future change is a deliberate one-line edit, not a silent library upgrade.
_hasher = PasswordHasher()


def hash_password(raw_password: str) -> str:
    """Hash a plaintext password. The raw password is never stored or logged."""
    return _hasher.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    """Constant-time-safe verify (argon2-cffi handles timing internally)."""
    try:
        return _hasher.verify(password_hash, raw_password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


# Why two async versions: Argon2id is deliberately slow and memory-hungry (that is what makes stolen hashes hard to
# crack). If an `async def` route calls it directly, the single event loop is frozen for the whole hash, and EVERY other
# student's request waits (measured on the project laptop: one sign-up stalled other requests; see docs/latency_results.md).
# asyncio.to_thread runs the hash on a worker thread, and argon2-cffi releases Python's lock while hashing,
# so other requests keep being served. The hash itself is unchanged.
async def hash_password_async(raw_password: str) -> str:
    return await asyncio.to_thread(hash_password, raw_password)


async def verify_password_async(raw_password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(verify_password, raw_password, password_hash)


def needs_rehash(password_hash: str) -> bool:
    """True if the stored hash was made with weaker-than-current parameters."""
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(user_id: uuid.UUID) -> str:
    """Issue a signed JWT identifying `user_id`, expiring per settings."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[uuid.UUID]:
    """Return the user id encoded in `token`, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
