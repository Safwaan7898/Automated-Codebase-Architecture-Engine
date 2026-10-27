"""Application configuration via pydantic-settings.

All settings can be overridden by environment variables or a .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.config import AISettings

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = (_BACKEND_DIR / "data").resolve()
_ENV_FILE = (_BACKEND_DIR / ".env").resolve()


class Settings(BaseSettings):
    """ArchLens application settings."""

    model_config = SettingsConfigDict(
        env_prefix="ARCHLENS_",
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Data Directory ──────────────────────────────────────────────────────
    data_dir: Path = _DEFAULT_DATA_DIR

    @property
    def resolved_data_dir(self) -> Path:
        env_val = os.environ.get("ARCHLENS_DATA_DIR")
        d = Path(env_val if env_val else self.data_dir).resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def analysis_db_path(self) -> Path:
        return self.resolved_data_dir / "archlens_analysis.db"

    @property
    def resolved_auth_db_path(self) -> Path:
        return self.resolved_data_dir / "archlens_auth.db"

    @property
    def cache_db_path(self) -> Path:
        return self.resolved_data_dir / "archlens_analysis_cache.db"

    @property
    def reports_storage_dir(self) -> Path:
        d = self.resolved_data_dir / ".reports_storage"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def workspaces_dir(self) -> Path:
        d = self.resolved_data_dir / "workspaces"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── Upload Limits ───────────────────────────────────────────────────────
    max_upload_size_mb: int = 100

    # ── Server ──────────────────────────────────────────────────────────────
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Logging ─────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: list[str] | str = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # ── Version ─────────────────────────────────────────────────────────────
    version: str = "0.1.0"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                import json

                try:
                    return json.loads(v_trimmed)
                except (json.JSONDecodeError, ValueError):
                    pass  # Fall back to comma-separated splitting below
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Authentication & RBAC ───────────────────────────────────────────────
    jwt_secret_key: str = "archlens-super-secure-production-jwt-signing-key-32bytes!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_max_failed_attempts: int = 5
    auth_lockout_minutes: int = 15
    auth_required: bool = False
    auth_db_path: str = "archlens_auth.db"
    admin_provision_key: str | None = None

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def ai(self) -> AISettings:
        from ai.config import get_ai_settings

        return get_ai_settings()


# Singleton — import this throughout the app
settings = Settings()
