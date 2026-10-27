"""Authentication and Role-Based Access Control (RBAC) package for ArchLens."""

from app.auth.dependencies import get_current_user, require_permission, require_role
from app.auth.models import (
    ROLE_PERMISSIONS,
    AuditLogEntry,
    Permission,
    Role,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserStatus,
)
from app.auth.service import auth_service
from app.auth.store import auth_store

__all__ = [
    "ROLE_PERMISSIONS",
    "AuditLogEntry",
    "Permission",
    "Role",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserStatus",
    "auth_service",
    "auth_store",
    "get_current_user",
    "require_permission",
    "require_role",
]
