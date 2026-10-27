"""User settings endpoints: profile updates, password modification, theme and notification preferences."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user
from app.auth.models import (
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserPreferencesRequest,
    UserResponse,
)
from app.auth.service import auth_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/profile", response_model=UserResponse)
def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    """Retrieve profile details for the authenticated employee."""
    return UserResponse.model_validate(user)


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """Update employee full name, department, or position."""
    return auth_service.update_profile(user["id"], payload)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Change account password. Verifies current password and revokes existing sessions."""
    client_ip = request.client.host if request.client else None
    auth_service.change_password(
        user_id=user["id"],
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=client_ip,
    )
    return {"message": "Password changed successfully. Please log in again with your new password."}


@router.get("/preferences")
def get_preferences(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Retrieve user theme and notification preferences."""
    return {
        "theme_preference": user.get("theme_preference", "dark"),
        "notification_preferences": user.get("notification_preferences", {}),
    }


@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    payload: UserPreferencesRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """Update user theme preference (dark/light/system) or notification subscriptions."""
    return auth_service.update_preferences(user["id"], payload)
