"""SQLite persistence store for users, refresh tokens, audit logs, and lockout state."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.auth.models import Role, UserStatus
from app.auth.security import hash_password
from app.core.config import settings

DEMO_USERS: list[dict[str, Any]] = [
    {
        "role": Role.ADMIN,
        "email": "admin@archlens.io",
        "password": "AdminPassword!2026",
        "full_name": "Eleanor Vance (Admin)",
        "employee_id": "EMP-001",
        "department": "Platform Architecture",
        "position": "Chief Systems Architect",
    },
    {
        "role": Role.ENGINEERING_MANAGER,
        "email": "manager@archlens.io",
        "password": "ManagerPassword!2026",
        "full_name": "Marcus Aurelius (Manager)",
        "employee_id": "EMP-002",
        "department": "Engineering Management",
        "position": "Director of Engineering",
    },
    {
        "role": Role.SENIOR_DEVELOPER,
        "email": "senior.dev@archlens.io",
        "password": "SeniorDevPassword!2026",
        "full_name": "Clara Oswald (Senior Dev)",
        "employee_id": "EMP-003",
        "department": "Core Engine",
        "position": "Principal Software Engineer",
    },
    {
        "role": Role.DEVELOPER,
        "email": "dev@archlens.io",
        "password": "DeveloperPassword!2026",
        "full_name": "Devon Parker (Developer)",
        "employee_id": "EMP-004",
        "department": "Core Engine",
        "position": "Software Engineer II",
    },
    {
        "role": Role.SECURITY_ANALYST,
        "email": "security@archlens.io",
        "password": "SecurityPassword!2026",
        "full_name": "Siddharth Thorne (Security)",
        "employee_id": "EMP-005",
        "department": "InfoSec & AppSec",
        "position": "Staff Security Analyst",
    },
    {
        "role": Role.QA_ENGINEER,
        "email": "qa@archlens.io",
        "password": "QAPassword!2026",
        "full_name": "Quinn Adams (QA)",
        "employee_id": "EMP-006",
        "department": "Quality & Verification",
        "position": "Senior QA Automation Engineer",
    },
    {
        "role": Role.VIEWER,
        "email": "viewer@archlens.io",
        "password": "ViewerPassword!2026",
        "full_name": "Victor Chen (Viewer)",
        "employee_id": "EMP-007",
        "department": "Product & Strategy",
        "position": "Product Specialist",
    },
]


class AuthStore:
    """Thread-safe SQLite database manager for user identities and security audit trails."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            self.db_path = settings.resolved_auth_db_path
        else:
            self.db_path = Path(db_path) if isinstance(db_path, str) and db_path != ":memory:" else db_path
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(
            str(self.db_path) if isinstance(self.db_path, Path) else self.db_path,
            timeout=3.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 3000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        try:
            yield conn
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cur = conn.cursor()

            # 1. Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    work_email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    employee_id TEXT NOT NULL UNIQUE,
                    department TEXT NOT NULL,
                    position TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT,
                    theme_preference TEXT DEFAULT 'dark',
                    notification_preferences TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 2. Refresh Tokens Table (Rotation & Revocation)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_revoked INTEGER DEFAULT 0,
                    replaced_by TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # 3. Audit Logs Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    details TEXT NOT NULL,
                    ip_address TEXT
                )
            """)

            conn.commit()

        # Seed initial demo accounts if not already present
        self.seed_demo_users()

    def seed_demo_users(self) -> None:
        """Seed 1 demo user per role for testing and development."""
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            for demo in DEMO_USERS:
                cur.execute("SELECT id FROM users WHERE LOWER(work_email) = LOWER(?)", (demo["email"],))
                if cur.fetchone() is None:
                    user_id = str(uuid.uuid4())
                    pwd_hash = hash_password(demo["password"])
                    cur.execute(
                        """
                        INSERT INTO users (
                            id, full_name, work_email, password_hash, employee_id,
                            department, position, role, status, failed_login_attempts,
                            locked_until, theme_preference, notification_preferences,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_id,
                            demo["full_name"],
                            demo["email"].lower(),
                            pwd_hash,
                            demo["employee_id"],
                            demo["department"],
                            demo["position"],
                            demo["role"].value if isinstance(demo["role"], Role) else demo["role"],
                            UserStatus.ACTIVE.value,
                            0,
                            None,
                            "dark",
                            json.dumps({"email_reports": True, "security_alerts": True}),
                            now,
                            now,
                        ),
                    )
            conn.commit()

    # ── User CRUD ────────────────────────────────────────────────────────────
    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            return self._row_to_user_dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE LOWER(work_email) = LOWER(?)", (email.strip(),))
            row = cur.fetchone()
            return self._row_to_user_dict(row) if row else None

    def get_user_by_employee_id(self, employee_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE UPPER(employee_id) = UPPER(?)", (employee_id.strip(),))
            row = cur.fetchone()
            return self._row_to_user_dict(row) if row else None

    def create_user(
        self,
        full_name: str,
        work_email: str,
        password_hash: str,
        employee_id: str,
        department: str,
        position: str,
        role: Role = Role.VIEWER,
        status: UserStatus = UserStatus.PENDING,
    ) -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (
                    id, full_name, work_email, password_hash, employee_id,
                    department, position, role, status, failed_login_attempts,
                    locked_until, theme_preference, notification_preferences,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 'dark', '{}', ?, ?)
            """,
                (
                    user_id,
                    full_name.strip(),
                    work_email.lower().strip(),
                    password_hash,
                    employee_id.strip(),
                    department.strip(),
                    position.strip(),
                    role.value if isinstance(role, Role) else role,
                    status.value if isinstance(status, UserStatus) else status,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_user_by_id(user_id)  # type: ignore[return-value]

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        valid_keys = {
            "full_name",
            "department",
            "position",
            "role",
            "status",
            "password_hash",
            "theme_preference",
            "notification_preferences",
            "failed_login_attempts",
            "locked_until",
        }
        filtered = {k: v for k, v in updates.items() if k in valid_keys}
        if not filtered:
            return self.get_user_by_id(user_id)

        filtered["updated_at"] = datetime.now(UTC).isoformat()
        if "role" in filtered and isinstance(filtered["role"], Role):
            filtered["role"] = filtered["role"].value
        if "status" in filtered and isinstance(filtered["status"], UserStatus):
            filtered["status"] = filtered["status"].value
        if "notification_preferences" in filtered and isinstance(filtered["notification_preferences"], dict):
            filtered["notification_preferences"] = json.dumps(filtered["notification_preferences"])

        set_clause = ", ".join(f"{k} = ?" for k in filtered.keys())
        values = [*list(filtered.values()), user_id]

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()

        return self.get_user_by_id(user_id)

    def list_users(
        self,
        role: Role | None = None,
        status: UserStatus | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM users WHERE 1=1"
        params: list[Any] = []
        if role:
            query += " AND role = ?"
            params.append(role.value if isinstance(role, Role) else role)
        if status:
            query += " AND status = ?"
            params.append(status.value if isinstance(status, UserStatus) else status)

        query += " ORDER BY created_at DESC"
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_user_dict(r) for r in rows]

    # ── Lockout & Brute Force Protection ─────────────────────────────────────
    def record_failed_login(
        self,
        user_id: str,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
    ) -> tuple[int, bool, datetime | None]:
        """Increment failed attempts; lock user if threshold reached."""
        user = self.get_user_by_id(user_id)
        if not user:
            return 0, False, None

        current_fails = (user.get("failed_login_attempts") or 0) + 1
        now = datetime.now(UTC)
        locked = False
        locked_until_dt: datetime | None = None

        updates: dict[str, Any] = {"failed_login_attempts": current_fails}
        if current_fails >= max_attempts:
            locked = True
            locked_until_dt = now + timedelta(minutes=lockout_minutes)
            updates["status"] = UserStatus.LOCKED.value
            updates["locked_until"] = locked_until_dt.isoformat()

        self.update_user(user_id, updates)
        return current_fails, locked, locked_until_dt

    def reset_failed_logins(self, user_id: str) -> None:
        """Reset failed attempt counters upon successful login."""
        self.update_user(
            user_id,
            {
                "failed_login_attempts": 0,
                "locked_until": None,
            },
        )

    def is_user_locked(self, user: dict[str, Any]) -> tuple[bool, str | None]:
        """Check if user account is locked and if temporary lockout is still active."""
        if user.get("status") != UserStatus.LOCKED.value:
            return False, None

        locked_until_str = user.get("locked_until")
        if not locked_until_str:
            return True, "Account is permanently locked. Please contact an administrator."

        try:
            locked_until = datetime.fromisoformat(locked_until_str)
            now = datetime.now(UTC)
            if now < locked_until:
                remaining = int((locked_until - now).total_seconds() / 60) + 1
                msg = f"Account temporarily locked due to repeated failed logins. Try again in {remaining} minute(s)."
                return True, msg
            else:
                # Lockout period expired: auto-unlock
                self.update_user(
                    user["id"],
                    {
                        "status": UserStatus.ACTIVE.value,
                        "failed_login_attempts": 0,
                        "locked_until": None,
                    },
                )
                return False, None
        except Exception:
            return True, "Account is locked."

    # ── Refresh Token Store (Rotation & Revocation) ───────────────────────────
    def save_refresh_token(
        self,
        jti: str,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO refresh_tokens (
                    id, user_id, token_hash, expires_at, is_revoked, replaced_by, created_at
                ) VALUES (?, ?, ?, ?, 0, NULL, ?)
            """,
                (jti, user_id, token_hash, expires_at.isoformat(), now),
            )
            conn.commit()

    def get_refresh_token(self, jti: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM refresh_tokens WHERE id = ?", (jti,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "user_id": row["user_id"],
                "token_hash": row["token_hash"],
                "expires_at": row["expires_at"],
                "is_revoked": bool(row["is_revoked"]),
                "replaced_by": row["replaced_by"],
                "created_at": row["created_at"],
            }

    def revoke_refresh_token(self, jti: str, replaced_by: str | None = None) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE refresh_tokens
                SET is_revoked = 1, replaced_by = ?
                WHERE id = ?
            """,
                (replaced_by, jti),
            )
            conn.commit()

    def revoke_all_user_tokens(self, user_id: str) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE refresh_tokens SET is_revoked = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

    # ── Audit Log ─────────────────────────────────────────────────────────────
    def add_audit_log(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> str:
        log_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_logs (
                    id, timestamp, user_id, user_email, user_role, action,
                    resource_type, resource_id, details, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    log_id,
                    now,
                    user_id,
                    user_email,
                    user_role,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(details or {}),
                    ip_address,
                ),
            )
            conn.commit()
        return log_id

    def get_audit_logs(
        self,
        user_email: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params: list[Any] = []
        if user_email:
            query += " AND LOWER(user_email) = LOWER(?)"
            params.append(user_email.strip())
        if action:
            query += " AND action = ?"
            params.append(action.strip())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            logs = []
            for r in rows:
                details = {}
                try:
                    details = json.loads(r["details"])
                except Exception:
                    pass
                logs.append(
                    {
                        "id": r["id"],
                        "timestamp": r["timestamp"],
                        "user_id": r["user_id"],
                        "user_email": r["user_email"],
                        "user_role": r["user_role"],
                        "action": r["action"],
                        "resource_type": r["resource_type"],
                        "resource_id": r["resource_id"],
                        "details": details,
                        "ip_address": r["ip_address"],
                    }
                )
            return logs

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _row_to_user_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        notif_prefs = {}
        try:
            notif_prefs = json.loads(row["notification_preferences"])
        except Exception:
            pass

        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "work_email": row["work_email"],
            "password_hash": row["password_hash"],
            "employee_id": row["employee_id"],
            "department": row["department"],
            "position": row["position"],
            "role": Role(row["role"]),
            "status": UserStatus(row["status"]),
            "failed_login_attempts": row["failed_login_attempts"],
            "locked_until": row["locked_until"],
            "theme_preference": row["theme_preference"],
            "notification_preferences": notif_prefs,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


# Global store instance
auth_store = AuthStore()
