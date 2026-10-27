"""Data models, enums, and schemas for authentication and RBAC."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Role(str, Enum):
    """System roles ordered by access level."""

    ADMIN = "ADMIN"
    ENGINEERING_MANAGER = "ENGINEERING_MANAGER"
    SENIOR_DEVELOPER = "SENIOR_DEVELOPER"
    DEVELOPER = "DEVELOPER"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    QA_ENGINEER = "QA_ENGINEER"
    VIEWER = "VIEWER"


class UserStatus(str, Enum):
    """User account lifecycle status."""

    PENDING = "pending"
    ACTIVE = "active"
    LOCKED = "locked"


# ── Granular Permissions ──────────────────────────────────────────────────────
class Permission:
    VIEW_DASHBOARD = "view:dashboard"
    VIEW_GRAPH = "view:graph"
    VIEW_METRICS = "view:metrics"
    VIEW_SMELLS = "view:smells"
    VIEW_REPORTS = "view:reports"
    RUN_INGESTION = "run:ingestion"
    VIEW_REFACTOR = "view:refactor"
    APPROVE_REFACTOR = "approve:refactor"
    GENERATE_REPORTS = "generate:reports"
    VIEW_SECURITY_FINDINGS = "view:security_findings"
    EXPORT_SECURITY_REPORTS = "export:security_reports"
    VIEW_TEAM_ANALYTICS = "view:team_analytics"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT_LOGS = "view:audit_logs"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.VIEWER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_REPORTS,
    },
    Role.DEVELOPER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_SMELLS,
        Permission.VIEW_REPORTS,
        Permission.RUN_INGESTION,
        Permission.VIEW_REFACTOR,
        Permission.GENERATE_REPORTS,
    },
    Role.SENIOR_DEVELOPER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_SMELLS,
        Permission.VIEW_REPORTS,
        Permission.RUN_INGESTION,
        Permission.VIEW_REFACTOR,
        Permission.APPROVE_REFACTOR,
        Permission.GENERATE_REPORTS,
    },
    Role.SECURITY_ANALYST: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_SMELLS,
        Permission.VIEW_REPORTS,
        Permission.RUN_INGESTION,
        Permission.VIEW_REFACTOR,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_SECURITY_FINDINGS,
        Permission.EXPORT_SECURITY_REPORTS,
    },
    Role.QA_ENGINEER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_SMELLS,
        Permission.VIEW_REPORTS,
        Permission.GENERATE_REPORTS,
        # Explicit: NO run:ingestion
    },
    Role.ENGINEERING_MANAGER: {
        # Everything except user administration and audit log
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_SMELLS,
        Permission.VIEW_REPORTS,
        Permission.RUN_INGESTION,
        Permission.VIEW_REFACTOR,
        Permission.APPROVE_REFACTOR,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_SECURITY_FINDINGS,
        Permission.EXPORT_SECURITY_REPORTS,
        Permission.VIEW_TEAM_ANALYTICS,
    },
    Role.ADMIN: {
        # Everything, plus user management and audit log
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_GRAPH,
        Permission.VIEW_METRICS,
        Permission.VIEW_SMELLS,
        Permission.VIEW_REPORTS,
        Permission.RUN_INGESTION,
        Permission.VIEW_REFACTOR,
        Permission.APPROVE_REFACTOR,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_SECURITY_FINDINGS,
        Permission.EXPORT_SECURITY_REPORTS,
        Permission.VIEW_TEAM_ANALYTICS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS,
    },
}


# ── Request / Response Schemas ───────────────────────────────────────────────
class UserCreate(BaseModel):
    """Self-registration request payload."""

    full_name: str = Field(..., min_length=2, max_length=120, description="Employee full legal name")
    work_email: EmailStr = Field(..., description="Corporate work email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")
    employee_id: str = Field(..., min_length=2, max_length=50, description="Company Employee ID, e.g. EMP-1042")
    department: str = Field(..., min_length=2, max_length=100, description="Employee department")
    position: str = Field(..., min_length=2, max_length=100, description="Job title / role in company")
    role: Role | None = Field(
        None,
        description="Requested role. Note: Self-registration always creates VIEWER in pending status.",
    )


class AdminCreate(BaseModel):
    """Admin registration payload with master authorization key."""

    full_name: str = Field(..., min_length=2, max_length=120, description="Administrator full name")
    work_email: EmailStr = Field(..., description="Administrator corporate email")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    employee_id: str = Field(..., min_length=2, max_length=50, description="Admin badge ID, e.g. ADM-001")
    department: str = Field(default="Architecture & Security Operations", min_length=2, max_length=100)
    position: str = Field(default="Lead System Architect", min_length=2, max_length=100)
    admin_key: str = Field(..., description="Master security provisioning key")


class UserStatusCheckResponse(BaseModel):
    """Status lookup response for pending applicants."""

    found: bool
    status: str | None = None
    full_name: str | None = None
    employee_id: str | None = None
    role: str | None = None
    department: str | None = None
    message: str


class UserLogin(BaseModel):
    """User login request payload."""

    work_email: EmailStr = Field(..., description="Registered work email")
    password: str = Field(..., description="Account password")


class RefreshRequest(BaseModel):
    """Optional payload when refreshing via JSON body instead of cookies."""

    refresh_token: str | None = Field(None, description="Optional refresh token string")


class UserResponse(BaseModel):
    """Sanitized user representation (no passwords or secrets)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    work_email: str
    employee_id: str
    department: str
    position: str
    role: Role
    status: UserStatus
    theme_preference: str = "dark"
    notification_preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class UserMeResponse(BaseModel):
    """Payload for GET /auth/me for frontend UI gating."""

    user: UserResponse
    permissions: list[str]


class TokenResponse(BaseModel):
    """JWT Token emission payload."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds
    role: Role
    permissions: list[str]


class ApproveUserRequest(BaseModel):
    """Admin approval and final role assignment payload."""

    role: Role = Field(..., description="Approved role for the employee")


class ChangeRoleRequest(BaseModel):
    """Admin role modification payload."""

    role: Role = Field(..., description="New role for the user")


class ChangePasswordRequest(BaseModel):
    """User password change payload."""

    current_password: str = Field(..., description="Existing account password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New secure password")


class UpdateProfileRequest(BaseModel):
    """User profile update payload."""

    full_name: str | None = Field(None, min_length=2, max_length=120)
    department: str | None = Field(None, min_length=2, max_length=100)
    position: str | None = Field(None, min_length=2, max_length=100)


class UserPreferencesRequest(BaseModel):
    """Settings update for theme and notifications."""

    theme_preference: str | None = Field(None, pattern="^(dark|light|system)$")
    notification_preferences: dict[str, Any] | None = None


class AuditLogEntry(BaseModel):
    """System audit trail entry for tracking critical actions."""

    id: str
    timestamp: str
    user_id: str
    user_email: str
    user_role: str
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None


class DemoUser(BaseModel):
    """Demo user descriptor for testing."""

    role: Role
    email: str
    password: str
    full_name: str
    employee_id: str
    department: str
    position: str
