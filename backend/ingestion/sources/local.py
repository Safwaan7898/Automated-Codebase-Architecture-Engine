"""Local filesystem path ingestion source.

Security:
- Disabled by default. Only enabled when ARCHLENS_ALLOW_LOCAL_PATHS=true.
- Validates path exists and copies files into the isolated workspace directory.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from ingestion.config import IngestionLimits
from ingestion.exceptions import LimitExceeded, LocalPathDisabledError, SourceError
from ingestion.hash_utils import hash_dict
from ingestion.models import IngestionSource, JobStatus, ProgressReporter

logger = logging.getLogger(__name__)


class LocalPathSource(IngestionSource):
    """Ingests files from a local directory path on the server."""

    def __init__(self, path: str | Path) -> None:
        self.raw_path = str(path).strip()
        p = Path(self.raw_path).resolve()
        if not p.exists():
            workspace_root = Path(__file__).resolve().parent.parent.parent.parent
            candidates = [
                (Path.cwd().parent / self.raw_path).resolve(),
                (workspace_root / self.raw_path).resolve(),
            ]
            for candidate in candidates:
                if candidate.exists():
                    p = candidate
                    break
        self.path = p

    @property
    def source_type(self) -> str:
        return "local"

    @property
    def display_name(self) -> str:
        return str(self.path)

    @property
    def repo_name(self) -> str:
        return self.path.name or "local_repo"

    @property
    def source_hash(self) -> str:
        return hash_dict({"type": "local", "path": str(self.path)})

    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        # 1. Feature flag guard
        if not limits.allow_local_paths:
            raise LocalPathDisabledError()

        # 2. Validation
        if not self.path.exists():
            raise SourceError(f"Local path does not exist: '{self.raw_path}'")
        if not self.path.is_dir():
            raise SourceError(f"Local path is not a directory: '{self.raw_path}'")

        await progress(JobStatus.EXTRACTING, "copying_local", 20.0, f"Copying files from {self.path.name}")

        skip_set = {d.lower() for d in limits.skip_dirs}
        file_count = 0
        total_bytes = 0

        # Copy files respecting skip dirs and limits
        for item in self.path.rglob("*"):
            if item.is_symlink():
                continue

            rel_parts = item.relative_to(self.path).parts
            if any(part.lower() in skip_set for part in rel_parts[:-1]):
                continue

            if item.is_file():
                file_count += 1
                if file_count > limits.max_files:
                    raise LimitExceeded(f"Local directory contains more than {limits.max_files} files.")

                size = item.stat().st_size
                if size > limits.max_file_size_bytes:
                    continue

                total_bytes += size
                if total_bytes > limits.max_uncompressed_bytes:
                    raise LimitExceeded(f"Total size exceeds limit of {limits.max_uncompressed_bytes} bytes.")

                dest_file = src_dir / item.relative_to(self.path)
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)

        await progress(JobStatus.EXTRACTING, "complete", 100.0, f"Copied {file_count} files from local path.")

        return {
            "source_path": str(self.path),
            "files_copied": file_count,
            "total_bytes": total_bytes,
        }
