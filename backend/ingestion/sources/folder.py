"""Folder upload ingestion source.

Supports:
- Browser directory/folder uploads (preserving nested directory structure)
- Enforces path safety: no '..' traversal, no absolute paths
- Enforces resource limits on file count, single file size, and total bytes
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ingestion.config import IngestionLimits
from ingestion.exceptions import EmptyArchiveError, LimitExceeded, SecurityError
from ingestion.hash_utils import hash_bytes
from ingestion.language_detector import is_binary_file
from ingestion.models import IngestionSource, JobStatus, ProgressReporter

logger = logging.getLogger(__name__)


class FolderUploadSource(IngestionSource):
    """Ingests a folder uploaded as a list of relative paths and file byte contents."""

    def __init__(
        self,
        files: list[tuple[str, bytes]],
        folder_name: str = "uploaded_folder",
    ) -> None:
        self.files = files
        self.folder_name = folder_name
        # Compute deterministic hash of all paths + contents
        combined_hasher = []
        for rel_path, content in sorted(files, key=lambda x: x[0]):
            combined_hasher.append(f"{rel_path}:{hash_bytes(content)}")
        self._hash = hash_bytes(";".join(combined_hasher).encode("utf-8"))

    @property
    def source_type(self) -> str:
        return "folder"

    @property
    def display_name(self) -> str:
        return self.folder_name

    @property
    def repo_name(self) -> str:
        return self.folder_name

    @property
    def source_hash(self) -> str:
        return self._hash

    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        total_files = len(self.files)
        if total_files > limits.max_files:
            raise LimitExceeded(f"Uploaded folder contains {total_files} files, exceeding limit of {limits.max_files}.")

        await progress(JobStatus.EXTRACTING, "writing_folder", 10.0, f"Writing {total_files} uploaded files...")

        resolved_src = src_dir.resolve()
        written = 0
        skipped = 0
        total_bytes = 0

        skip_set = {d.lower() for d in limits.skip_dirs} | {
            "node_modules",
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".env",
            "dist",
            "build",
            ".next",
            ".nuxt",
            ".cache",
            ".turbo",
            ".idea",
            ".vscode",
            "target",
            ".reports_storage",
        }

        for rel_path, content in self.files:
            # 1. Path safety checks
            clean_path = rel_path.strip().replace("\\", "/").lstrip("/")
            if not clean_path:
                continue

            parts = Path(clean_path).parts
            if ".." in parts:
                raise SecurityError(f"Unsafe path rejected: Path traversal '..' detected in uploaded file path: '{rel_path}'")

            if any(part.lower() in skip_set for part in parts):
                skipped += 1
                continue

            target_file = (resolved_src / clean_path).resolve()
            try:
                target_file.relative_to(resolved_src)
            except ValueError:
                raise SecurityError(f"Unsafe path rejected: uploaded file path '{rel_path}' resolves outside workspace.") from None

            # 2. Size limit checks
            content_size = len(content)
            if content_size > limits.max_file_size_bytes:
                logger.warning("Skipping file '%s' exceeding single file size limit.", rel_path)
                skipped += 1
                continue

            total_bytes += content_size
            if total_bytes > limits.max_uncompressed_bytes:
                msg = f"Folder total uncompressed size exceeds limit of {limits.max_uncompressed_bytes} bytes."
                raise LimitExceeded(msg)

            # 3. Write file
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with target_file.open("wb") as f:
                f.write(content)

            if is_binary_file(target_file):
                target_file.unlink(missing_ok=True)
                skipped += 1
                continue

            written += 1
            if written % 100 == 0:
                pct = 10.0 + (written / max(1, total_files)) * 80.0
                await progress(JobStatus.EXTRACTING, "writing_folder", pct, f"Saved {written}/{total_files} files...")

        if written == 0:
            raise EmptyArchiveError("Uploaded folder contains no valid source files.")

        await progress(JobStatus.EXTRACTING, "complete", 100.0, f"Saved {written} files (skipped {skipped} ignored/binary files).")

        return {
            "folder_name": self.folder_name,
            "files_written": written,
            "files_skipped": skipped,
            "total_bytes": total_bytes,
        }
