"""Admin endpoints: user approvals, role assignments, account unlock, and audit logs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.auth.models import (
    ApproveUserRequest,
    AuditLogEntry,
    ChangeRoleRequest,
    Permission,
    Role,
    UserResponse,
    UserStatus,
)
from app.auth.service import auth_service
from app.auth.store import auth_store

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def list_users(
    role: Role | None = None,
    status: UserStatus | None = None,
) -> list[UserResponse]:
    """List all registered users with optional role or status filtering. Admin only."""
    users = auth_store.list_users(role=role, status=status)
    return [UserResponse.model_validate(u) for u in users]


@router.post(
    "/users/{user_id}/approve",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def approve_user(
    user_id: str,
    payload: ApproveUserRequest,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_permission(Permission.MANAGE_USERS)),
) -> UserResponse:
    """Approve a pending user registration and assign their permanent company role. Admin only."""
    client_ip = request.client.host if request.client else None
    return auth_service.approve_user(
        user_id=user_id,
        role=payload.role,
        admin_user=admin_user,
        ip_address=client_ip,
    )


@router.post(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def change_role(
    user_id: str,
    payload: ChangeRoleRequest,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_permission(Permission.MANAGE_USERS)),
) -> UserResponse:
    """Change an existing user's RBAC role. Admin only."""
    client_ip = request.client.host if request.client else None
    return auth_service.change_role(
        user_id=user_id,
        role=payload.role,
        admin_user=admin_user,
        ip_address=client_ip,
    )


@router.post(
    "/users/{user_id}/unlock",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def unlock_user(
    user_id: str,
    request: Request,
    admin_user: dict[str, Any] = Depends(require_permission(Permission.MANAGE_USERS)),
) -> UserResponse:
    """Manually clear failed login lockout and re-enable a user account. Admin only."""
    client_ip = request.client.host if request.client else None
    return auth_service.unlock_user(
        user_id=user_id,
        admin_user=admin_user,
        ip_address=client_ip,
    )


@router.get(
    "/audit-logs",
    response_model=list[AuditLogEntry],
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
)
def get_audit_logs(
    user_email: str | None = Query(None, description="Filter by user work email"),
    action: str | None = Query(None, description="Filter by action name"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to retrieve"),
) -> list[AuditLogEntry]:
    """Inspect immutable audit log of critical system operations. Admin only."""
    logs = auth_store.get_audit_logs(user_email=user_email, action=action, limit=limit)
    return [AuditLogEntry.model_validate(log) for log in logs]


@router.get(
    "/ai/status",
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
)
def get_ai_status(
    admin_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
) -> dict[str, Any]:
    """Inspect AI engine provider health, cooldowns, and remaining quota. Admin only. Never exposes keys."""
    from ai import GLOBAL_AI_SERVICE

    return GLOBAL_AI_SERVICE.get_status().model_dump()


@router.get(
    "/ai/usage",
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
)
def get_ai_usage(
    admin_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
) -> dict[str, Any]:
    """Inspect AI engine call volume, token counts, and cost telemetry. Admin only."""
    from ai.features import get_ai_usage_statistics

    return get_ai_usage_statistics().model_dump()


# Direct router mounted at /admin for explicit path compatibility
direct_admin_ai_router = APIRouter(prefix="/admin", tags=["admin"])


@direct_admin_ai_router.get(
    "/ai/status",
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
)
def direct_get_ai_status(
    admin_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
) -> dict[str, Any]:
    """Inspect AI engine provider health, cooldowns, and remaining quota. Admin only. Never exposes keys."""
    from ai import GLOBAL_AI_SERVICE

    return GLOBAL_AI_SERVICE.get_status().model_dump()


@direct_admin_ai_router.get(
    "/ai/usage",
    dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
)
def direct_get_ai_usage(
    admin_user: dict[str, Any] = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
) -> dict[str, Any]:
    """Inspect AI engine call volume, token counts, and cost telemetry. Admin only."""
    from ai.features import get_ai_usage_statistics

    return get_ai_usage_statistics().model_dump()
