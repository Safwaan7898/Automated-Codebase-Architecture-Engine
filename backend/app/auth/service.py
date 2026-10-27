"""Authentication, authorization, and audit trail business logic."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from app.auth.models import (
    ROLE_PERMISSIONS,
    Role,
    TokenResponse,
    UpdateProfileRequest,
    UserCreate,
    UserLogin,
    UserPreferencesRequest,
    UserResponse,
    UserStatus,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.auth.store import AuthStore, auth_store
from app.core.config import settings


class AuthService:
    """Core authentication domain service."""

    def __init__(self, store: AuthStore | None = None) -> None:
        self.store = store or auth_store

    def register(self, data: UserCreate, ip_address: str | None = None) -> UserResponse:
        """Register a new employee.

        Always assigns VIEWER role and PENDING status.
        Self-assignment of ADMIN or manager roles is strictly prevented.
        """
        # 1. Uniqueness checks
        if self.store.get_user_by_email(data.work_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{data.work_email}' already exists.",
            )
        if self.store.get_user_by_employee_id(data.employee_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with employee ID '{data.employee_id}' already exists.",
            )

        # 2. Hash password with bcrypt
        pwd_hash = hash_password(data.password)

        # 3. Create user — force role to VIEWER and status to PENDING
        created = self.store.create_user(
            full_name=data.full_name,
            work_email=data.work_email,
            password_hash=pwd_hash,
            employee_id=data.employee_id,
            department=data.department,
            position=data.position,
            role=Role.VIEWER,
            status=UserStatus.PENDING,
        )

        # 4. Audit trail
        self.store.add_audit_log(
            user_id=created["id"],
            user_email=created["work_email"],
            user_role=created["role"].value,
            action="user_registered",
            resource_type="user",
            resource_id=created["id"],
            details={
                "requested_role": data.role.value if data.role else None,
                "assigned_role": Role.VIEWER.value,
                "status": UserStatus.PENDING.value,
            },
            ip_address=ip_address,
        )

        return UserResponse.model_validate(created)

    def register_admin(self, data: Any, ip_address: str | None = None) -> UserResponse:
        """Register an administrator account with security master key validation."""
        required_key = settings.admin_provision_key
        if not required_key or not required_key.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public admin registration is disabled on this instance.",
            )
        provided_key = getattr(data, "admin_key", "")
        if not provided_key or not secrets.compare_digest(provided_key, required_key.strip()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Admin Master Key. Authorization denied.",
            )
        if self.store.get_user_by_email(data.work_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{data.work_email}' already exists.",
            )
        if self.store.get_user_by_employee_id(data.employee_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with employee ID '{data.employee_id}' already exists.",
            )
        pwd_hash = hash_password(data.password)
        created = self.store.create_user(
            full_name=data.full_name,
            work_email=data.work_email,
            password_hash=pwd_hash,
            employee_id=data.employee_id,
            department=data.department,
            position=data.position,
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        self.store.add_audit_log(
            user_id=created["id"],
            user_email=created["work_email"],
            user_role=Role.ADMIN.value,
            action="admin_provisioned",
            resource_type="user",
            resource_id=created["id"],
            details={"status": UserStatus.ACTIVE.value},
            ip_address=ip_address,
        )
        return UserResponse.model_validate(created)

    def check_status(self, identifier: str) -> dict[str, Any]:
        """Check employee registration approval status by work email or employee ID."""
        clean_id = identifier.strip()
        user = self.store.get_user_by_email(clean_id) or self.store.get_user_by_employee_id(clean_id)
        if not user:
            return {
                "found": False,
                "status": None,
                "message": f"No registered account found matching '{clean_id}'. Please submit registration first.",
            }
        st = user["status"]
        st_val = st.value if hasattr(st, "value") else str(st)
        role_val = user["role"].value if hasattr(user["role"], "value") else str(user["role"])
        return {
            "found": True,
            "status": st_val,
            "full_name": user["full_name"],
            "employee_id": user["employee_id"],
            "role": role_val,
            "department": user["department"],
            "message": (
                "Account is pending administrator approval. An admin must verify your employee ID before login."
                if st_val == "pending"
                else "Account is approved and active. You may proceed to login."
            ),
        }

    def login(self, data: UserLogin, ip_address: str | None = None) -> tuple[UserResponse, TokenResponse]:
        """Authenticate user with work email and password.

        Enforces brute force lockout and verifies active status.
        """
        user = self.store.get_user_by_email(data.work_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid work email or password.",
            )

        # 1. Check if user is currently locked
        is_locked, lock_message = self.store.is_user_locked(user)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=lock_message or "Account is temporarily locked. Please try again later.",
            )

        # 2. Verify password
        if not verify_password(data.password, user["password_hash"]):
            fails, locked, locked_until = self.store.record_failed_login(
                user["id"],
                max_attempts=settings.auth_max_failed_attempts,
                lockout_minutes=settings.auth_lockout_minutes,
            )
            if locked:
                self.store.add_audit_log(
                    user_id=user["id"],
                    user_email=user["work_email"],
                    user_role=user["role"].value,
                    action="account_locked",
                    resource_type="user",
                    resource_id=user["id"],
                    details={
                        "consecutive_failures": fails,
                        "locked_until": locked_until.isoformat() if locked_until else None,
                    },
                    ip_address=ip_address,
                )
                lock_msg = (
                    f"Account locked after {fails} consecutive failed login attempts. "
                    f"Try again in {settings.auth_lockout_minutes} minutes."
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=lock_msg,
                )

            remaining = settings.auth_max_failed_attempts - fails
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid work email or password. {remaining} attempt(s) remaining before lockout.",
            )

        # 3. Check account lifecycle status (Pending vs Active)
        if user["status"] == UserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account registration is pending administrator approval.",
            )
        if user["status"] == UserStatus.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account is currently locked.",
            )

        # 4. Success — reset failed login counter
        self.store.reset_failed_logins(user["id"])

        # 5. Issue access token and refresh token
        user_role = user["role"]
        permissions = sorted(ROLE_PERMISSIONS.get(user_role, set()))
        access_token = create_access_token(
            user_id=user["id"],
            email=user["work_email"],
            role=user_role,
            permissions=permissions,
        )

        refresh_token, jti = create_refresh_token(user_id=user["id"])
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        self.store.save_refresh_token(
            jti=jti,
            user_id=user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # 6. Audit trail
        self.store.add_audit_log(
            user_id=user["id"],
            user_email=user["work_email"],
            user_role=user_role.value,
            action="user_login",
            resource_type="auth",
            resource_id=user["id"],
            details={"ip": ip_address},
            ip_address=ip_address,
        )

        token_resp = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            role=user_role,
            permissions=permissions,
            expires_in=settings.access_token_expire_minutes * 60,
        )
        return UserResponse.model_validate(user), token_resp

    def refresh(self, refresh_token_str: str, ip_address: str | None = None) -> TokenResponse:
        """Rotate refresh token: revoke current token and emit a new access/refresh pair.

        Detects token reuse: if a previously rotated token is reused, all user sessions are revoked.
        """
        try:
            payload = decode_token(refresh_token_str)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired refresh token: {e}",
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token provided is not a refresh token.",
            )

        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token payload.")

        token_record = self.store.get_refresh_token(jti)
        if not token_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found or expired.")

        # REUSE DETECTION: if token is already revoked and has a replaced_by pointer
        if token_record["is_revoked"]:
            if token_record.get("replaced_by"):
                # Potential token compromise: revoke ALL sessions for this user immediately!
                self.store.revoke_all_user_tokens(user_id)
                self.store.add_audit_log(
                    user_id=user_id,
                    user_email=f"user_{user_id}",
                    user_role="UNKNOWN",
                    action="refresh_token_reuse_detected",
                    resource_type="auth",
                    resource_id=jti,
                    details={"warning": "All refresh tokens revoked due to reuse detection."},
                    ip_address=ip_address,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Security alert: refresh token reuse detected. All active sessions have been revoked.",
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked.")

        # Verify user still exists and is active
        user = self.store.get_user_by_id(user_id)
        if not user or user["status"] != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive, pending, or locked.",
            )

        # Issue new token pair
        user_role = user["role"]
        permissions = sorted(ROLE_PERMISSIONS.get(user_role, set()))
        new_access_token = create_access_token(
            user_id=user["id"],
            email=user["work_email"],
            role=user_role,
            permissions=permissions,
        )
        new_refresh_token, new_jti = create_refresh_token(user_id=user["id"])
        new_token_hash = hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        # Mark old token as revoked and rotated
        self.store.revoke_refresh_token(jti, replaced_by=new_jti)
        self.store.save_refresh_token(
            jti=new_jti,
            user_id=user["id"],
            token_hash=new_token_hash,
            expires_at=expires_at,
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            role=user_role,
            permissions=permissions,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    def logout(self, refresh_token_str: str | None, current_user_id: str | None = None) -> None:
        """Revoke refresh token on logout."""
        if refresh_token_str:
            try:
                payload = decode_token(refresh_token_str)
                jti = payload.get("jti")
                if jti:
                    self.store.revoke_refresh_token(jti)
            except Exception:
                pass

        if current_user_id:
            user = self.store.get_user_by_id(current_user_id)
            if user:
                self.store.add_audit_log(
                    user_id=user["id"],
                    user_email=user["work_email"],
                    user_role=user["role"].value,
                    action="user_logout",
                    resource_type="auth",
                    resource_id=user["id"],
                )

    def approve_user(
        self,
        user_id: str,
        role: Role,
        admin_user: dict[str, Any],
        ip_address: str | None = None,
    ) -> UserResponse:
        """Admin approves a pending user and assigns their operational role."""
        target = self.store.get_user_by_id(user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        updated = self.store.update_user(
            user_id,
            {
                "role": role,
                "status": UserStatus.ACTIVE,
            },
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user.")

        self.store.add_audit_log(
            user_id=admin_user["id"],
            user_email=admin_user["work_email"],
            user_role=admin_user["role"].value,
            action="user_approved",
            resource_type="user",
            resource_id=user_id,
            details={"assigned_role": role.value, "target_email": target["work_email"]},
            ip_address=ip_address,
        )

        return UserResponse.model_validate(updated)

    def change_role(
        self,
        user_id: str,
        role: Role,
        admin_user: dict[str, Any],
        ip_address: str | None = None,
    ) -> UserResponse:
        """Admin alters an existing user's role."""
        target = self.store.get_user_by_id(user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        old_role = target["role"].value
        updated = self.store.update_user(user_id, {"role": role})

        self.store.add_audit_log(
            user_id=admin_user["id"],
            user_email=admin_user["work_email"],
            user_role=admin_user["role"].value,
            action="role_changed",
            resource_type="user",
            resource_id=user_id,
            details={"previous_role": old_role, "new_role": role.value, "target_email": target["work_email"]},
            ip_address=ip_address,
        )

        return UserResponse.model_validate(updated)

    def unlock_user(
        self,
        user_id: str,
        admin_user: dict[str, Any],
        ip_address: str | None = None,
    ) -> UserResponse:
        """Admin manually unlocks a locked user account."""
        target = self.store.get_user_by_id(user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        updated = self.store.update_user(
            user_id,
            {
                "status": UserStatus.ACTIVE,
                "failed_login_attempts": 0,
                "locked_until": None,
            },
        )

        self.store.add_audit_log(
            user_id=admin_user["id"],
            user_email=admin_user["work_email"],
            user_role=admin_user["role"].value,
            action="account_unlocked",
            resource_type="user",
            resource_id=user_id,
            details={"target_email": target["work_email"]},
            ip_address=ip_address,
        )

        return UserResponse.model_validate(updated)

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        """Change user password after verifying current credentials."""
        user = self.store.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        if not verify_password(current_password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed.",
            )

        new_hash = hash_password(new_password)
        self.store.update_user(user_id, {"password_hash": new_hash})

        # Revoke all existing sessions for security
        self.store.revoke_all_user_tokens(user_id)

        self.store.add_audit_log(
            user_id=user["id"],
            user_email=user["work_email"],
            user_role=user["role"].value,
            action="password_changed",
            resource_type="user",
            resource_id=user["id"],
            ip_address=ip_address,
        )

    def update_profile(self, user_id: str, updates: UpdateProfileRequest) -> UserResponse:
        """Update employee profile metadata."""
        fields = updates.model_dump(exclude_unset=True, exclude_none=True)
        updated = self.store.update_user(user_id, fields)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return UserResponse.model_validate(updated)

    def update_preferences(self, user_id: str, updates: UserPreferencesRequest) -> UserResponse:
        """Update theme and notification preferences."""
        fields = updates.model_dump(exclude_unset=True, exclude_none=True)
        updated = self.store.update_user(user_id, fields)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return UserResponse.model_validate(updated)


# Global service instance
auth_service = AuthService()
