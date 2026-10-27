"""FastAPI dependencies for authentication and role-based access control (RBAC)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.auth.models import ROLE_PERMISSIONS, Role, UserStatus
from app.auth.security import decode_token
from app.auth.store import auth_store
from app.core.config import settings

# Fallback development user when settings.auth_required is False and no token is passed
DEV_ADMIN_USER: dict[str, Any] = {
    "id": "dev-admin-system-id",
    "full_name": "ArchLens System Developer",
    "work_email": "admin@archlens.io",
    "employee_id": "EMP-001",
    "department": "Platform Architecture",
    "position": "Chief Systems Architect",
    "role": Role.ADMIN,
    "status": UserStatus.ACTIVE,
    "theme_preference": "dark",
    "notification_preferences": {},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def extract_token_from_request(request: Request) -> str | None:
    """Extract access token from cookie, Authorization Bearer header, or query param."""
    # 1. Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    # 2. Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 3. Query param (useful for downloads, SSE, or WebSocket connections)
    query_token = request.query_params.get("token")
    if query_token:
        return query_token

    return None


async def get_current_user(request: Request) -> dict[str, Any]:
    """Retrieve and validate the currently authenticated user.

    If a token is provided, it is strictly validated.
    If no token is provided:
      - When settings.auth_required is True: raises 401 Unauthorized.
      - When settings.auth_required is False: provides a default active development user
        to maintain backward compatibility with non-authenticated unit tests.
    """
    token = extract_token_from_request(request)

    if not token:
        if settings.auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
            )
        # Development / non-auth test mode fallback
        return DEV_ADMIN_USER

    try:
        payload = decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {e}",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token provided is not a valid access token.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject identity.",
        )

    user = auth_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token no longer exists.",
        )

    # Check status
    if user["status"] == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been locked.",
        )

    if user["status"] == UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account registration is pending administrator approval.",
        )

    return user


def require_permission(permission: str) -> Callable[..., Any]:
    """FastAPI dependency factory enforcing a specific granular permission."""

    async def _permission_dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_role = user.get("role")
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has no assigned role.",
            )

        # Role enum conversion
        role_enum = user_role if isinstance(user_role, Role) else Role(user_role)
        allowed_permissions = ROLE_PERMISSIONS.get(role_enum, set())

        if permission not in allowed_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"Permission denied: role '{role_enum.value}' lacks required permission '{permission}'."),
            )

        return user

    return _permission_dependency


def require_role(*allowed_roles: Role) -> Callable[..., Any]:
    """FastAPI dependency factory restricting access to one or more specific roles."""
    expected_roles = {r.value if isinstance(r, Role) else str(r) for r in allowed_roles}

    async def _role_dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_role = user.get("role")
        user_role_val = user_role.value if isinstance(user_role, Role) else str(user_role)

        if user_role_val not in expected_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires one of {sorted(expected_roles)}, but user is '{user_role_val}'.",
            )

        return user

    return _role_dependency
