"""Workspace management and TTL-based cleanup.

Workspaces are isolated directories scoped by job_id:
    <workspace_root>/<job_id>/
        src/      <- source files extracted/cloned here
        meta.json <- optional saved workspace metadata

Provides:
- Workspace creation and path resolution
- Read-only filesystem marking
- Windows-friendly safe cleanup (clearing readonly bit before rmtree)
- TTL-based expiration and cleanup job
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

def _get_default_workspace_base() -> Path:
    try:
        from app.core.config import settings

        return settings.workspaces_dir
    except Exception:
        env_dir = os.environ.get("ARCHLENS_DATA_DIR")
        if env_dir:
            p = Path(env_dir).resolve() / "workspaces"
        else:
            p = Path(tempfile.gettempdir()) / "archlens_workspaces"
        p.mkdir(parents=True, exist_ok=True)
        return p


DEFAULT_WORKSPACE_BASE: Path = _get_default_workspace_base()


def _handle_remove_readonly(func, path, exc_info):
    """Clear readonly bit on Windows/POSIX and retry deletion."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception as exc:
        logger.debug("Failed to force delete %s: %s", path, exc)


@dataclass
class Workspace:
    job_id: str
    root: Path
    src_dir: Path
    created_at: float

    @property
    def is_expired(self) -> bool:
        return False


class WorkspaceManager:
    """Manages workspace lifecycle, read-only permissions, and TTL cleanup."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or _get_default_workspace_base()).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_workspace(self, job_id: str) -> Workspace:
        """Create and return a new isolated workspace for *job_id*."""
        root = (self.base_dir / job_id).resolve()
        src_dir = (root / "src").resolve()

        if root.exists():
            self.delete_workspace(job_id)

        src_dir.mkdir(parents=True, exist_ok=True)
        return Workspace(
            job_id=job_id,
            root=root,
            src_dir=src_dir,
            created_at=time.time(),
        )

    def get_workspace(self, job_id: str) -> Workspace | None:
        root = (self.base_dir / job_id).resolve()
        src_dir = root / "src"
        if root.exists() and src_dir.exists():
            try:
                ctime = root.stat().st_ctime
            except OSError:
                ctime = time.time()
            return Workspace(job_id=job_id, root=root, src_dir=src_dir, created_at=ctime)
        return None

    def make_read_only(self, path: Path) -> None:
        """Recursively mark files in path as read-only."""
        try:
            for p in path.rglob("*"):
                if p.is_file():
                    current = p.stat().st_mode
                    p.chmod(current & ~stat.S_IWRITE)
        except Exception as exc:
            logger.debug("Could not set read-only permissions on %s: %s", path, exc)

    def make_writable(self, path: Path) -> None:
        """Recursively restore write permissions for cleanup."""
        try:
            for p in path.rglob("*"):
                try:
                    p.chmod(stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
            path.chmod(stat.S_IWRITE | stat.S_IREAD)
        except Exception as exc:
            logger.debug("Could not restore write permissions on %s: %s", path, exc)

    def delete_workspace(self, job_id: str) -> None:
        """Delete workspace directory cleanly, handling readonly attributes."""
        root = (self.base_dir / job_id).resolve()
        if not root.exists():
            return

        self.make_writable(root)
        shutil.rmtree(root, onerror=_handle_remove_readonly)
        logger.info("Deleted workspace for job %s", job_id)

    def cleanup_expired(self, ttl_seconds: int) -> int:
        """Delete workspaces older than ttl_seconds. Returns number deleted."""
        now = time.time()
        deleted = 0
        if not self.base_dir.exists():
            return 0

        for child in self.base_dir.iterdir():
            if not child.is_dir():
                continue
            try:
                mtime = child.stat().st_mtime
                if (now - mtime) > ttl_seconds:
                    self.delete_workspace(child.name)
                    deleted += 1
            except Exception as exc:
                logger.warning("Error cleaning workspace %s: %s", child, exc)

        return deleted
