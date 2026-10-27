"""Authentication endpoints: registration, login, logout, token rotation, and me."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.dependencies import get_current_user
from app.auth.models import (
    ROLE_PERMISSIONS,
    AdminCreate,
    DemoUser,
    RefreshRequest,
    Role,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserMeResponse,
    UserResponse,
)
from app.auth.service import auth_service
from app.auth.store import DEMO_USERS
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, token_resp: TokenResponse) -> None:
    """Set httpOnly, Secure, SameSite cookies for access and refresh tokens."""
    # Access token cookie (15 minutes)
    response.set_cookie(
        key="access_token",
        value=token_resp.access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,  # type: ignore[arg-type]
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    # Refresh token cookie (7 days)
    response.set_cookie(
        key="refresh_token",
        value=token_resp.refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,  # type: ignore[arg-type]
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Delete access and refresh token cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, data: UserCreate) -> UserResponse:
    """Employee self-registration.

    Always creates accounts as VIEWER in 'pending' status.
    Administrator must approve account before user can sign in.
    """
    client_ip = request.client.host if request.client else None
    return auth_service.register(data, ip_address=client_ip)


@router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_admin(request: Request, data: AdminCreate) -> UserResponse:
    """Administrator registration requiring Master Security Authorization Key."""
    client_ip = request.client.host if request.client else None
    return auth_service.register_admin(data, ip_address=client_ip)


@router.get("/status/{identifier}")
def check_status(identifier: str) -> dict[str, Any]:
    """Check approval status of an employee account using work email or employee ID."""
    return auth_service.check_status(identifier)


@router.post("/login", response_model=TokenResponse)
def login(request: Request, response: Response, data: UserLogin) -> TokenResponse:
    """Authenticate with work email and password.

    Sets httpOnly, Secure, SameSite cookies and returns JWT tokens.
    Rate-limits login attempts and locks the account after repeated failures.
    """
    client_ip = request.client.host if request.client else None
    user, tokens = auth_service.login(data, ip_address=client_ip)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: Request, response: Response, payload: RefreshRequest | None = None) -> TokenResponse:
    """Rotate refresh token: issues a new access token and a new refresh token.

    Accepts refresh token from httpOnly cookie or JSON payload.
    Revokes the previous token and detects reuse attempts.
    """
    token_str = None
    if payload and payload.refresh_token:
        token_str = payload.refresh_token
    else:
        token_str = request.cookies.get("refresh_token")

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required via cookie or request body.",
        )

    client_ip = request.client.host if request.client else None
    new_tokens = auth_service.refresh(token_str, ip_address=client_ip)
    _set_auth_cookies(response, new_tokens)
    return new_tokens


@router.post("/logout")
def logout(request: Request, response: Response, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    """Log out user: clears cookies and revokes active refresh token."""
    refresh_token_cookie = request.cookies.get("refresh_token")
    auth_service.logout(refresh_token_cookie, current_user_id=user.get("id"))
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserMeResponse)
def get_me(user: dict[str, Any] = Depends(get_current_user)) -> UserMeResponse:
    """Return currently authenticated user details and permission list for UI gating."""
    role = user.get("role")
    role_enum = role if isinstance(role, Role) else Role(role)
    permissions = sorted(ROLE_PERMISSIONS.get(role_enum, set()))
    return UserMeResponse(
        user=UserResponse.model_validate(user),
        permissions=permissions,
    )


@router.get("/demo-users", response_model=list[DemoUser])
def list_demo_users() -> list[DemoUser]:
    """List seeded demo credentials for testing and pair programming."""
    return [
        DemoUser(
            role=d["role"],
            email=d["email"],
            password=d["password"],
            full_name=d["full_name"],
            employee_id=d["employee_id"],
            department=d["department"],
            position=d["position"],
        )
        for d in DEMO_USERS
    ]
