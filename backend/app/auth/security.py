"""Cryptographic security utilities: password hashing with bcrypt and JWT tokens."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.auth.models import Role
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt with automatic salt generation."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored bcrypt hash without logging."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


async def async_verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password in a worker threadpool so it never blocks the async event loop."""
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(verify_password, plain_password, hashed_password)


async def async_hash_password(password: str) -> str:
    """Hash password in a worker threadpool so it never blocks the async event loop."""
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(hash_password, password)


def create_access_token(
    user_id: str,
    email: str,
    role: Role,
    permissions: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT access token valid for 15 minutes by default."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role.value if isinstance(role, Role) else str(role),
        "permissions": permissions,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str,
    jti: str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """Generate a signed JWT refresh token (7 days) and return (token_string, jti)."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=settings.refresh_token_expire_days))
    token_id = jti or str(uuid.uuid4())

    payload: dict[str, Any] = {
        "sub": user_id,
        "jti": token_id,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    token_str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token_str, token_id


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate signature, expiry, and structure of a JWT token."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "type"]},
    )
