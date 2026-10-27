"""Archive upload ingestion source.

Supports:
- .zip, .tar, .tar.gz, .tgz, .tar.bz2
- Auto-detects format by magic bytes (not file extension)
- Full Zip Slip, Symlink escape, Zip Bomb, and nesting protections
- Deduplication via archive payload SHA-256
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from ingestion.config import IngestionLimits
from ingestion.exceptions import EmptyArchiveError, LimitExceeded, SourceError
from ingestion.hash_utils import hash_bytes, hash_file
from ingestion.models import IngestionSource, JobStatus, ProgressReporter
from ingestion.security import detect_archive_type, safe_extract_archive

logger = logging.getLogger(__name__)


class ArchiveUploadSource(IngestionSource):
    """Ingests source code from an uploaded archive file or bytes."""

    def __init__(
        self,
        archive_data: bytes | Path,
        filename: str = "archive.zip",
        language: str = "auto",
        include_tests: bool = False,
    ) -> None:
        self.filename = filename
        self.language = language
        self.include_tests = include_tests
        if isinstance(archive_data, Path):
            self._archive_path: Path | None = archive_data
            self._data: bytes | None = None
            self._hash = hash_file(archive_data)
        else:
            self._archive_path = None
            self._data = archive_data
            self._hash = hash_bytes(archive_data)

    @property
    def source_type(self) -> str:
        return "archive"

    @property
    def display_name(self) -> str:
        return self.filename

    @property
    def repo_name(self) -> str:
        # Strip archive extensions
        name = self.filename
        for ext in (".tar.gz", ".tar.bz2", ".tgz", ".zip", ".tar"):
            if name.lower().endswith(ext):
                name = name[: -len(ext)]
                break
        return name or "archive"

    @property
    def fingerprint(self) -> str:
        return self._hash.lower()

    @property
    def cache_key(self) -> str:
        from parsers.fingerprint import PARSER_VERSION, compute_settings_hash

        settings_hash = compute_settings_hash(
            {"language": self.language, "include_tests": self.include_tests}
        )
        return f"{self.fingerprint}:{PARSER_VERSION}:{settings_hash}:{self.language}"

    @property
    def source_hash(self) -> str:
        return f"{self._hash}:{self.language}"

    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        await progress(JobStatus.EXTRACTING, "inspecting_archive", 10.0, f"Analyzing archive '{self.filename}'")

        # Materialize archive to temporary file if in-memory bytes
        temp_file: Path | None = None
        if self._archive_path:
            archive_path = self._archive_path
            archive_size = archive_path.stat().st_size
        else:
            assert self._data is not None
            archive_size = len(self._data)
            tmp = tempfile.NamedTemporaryFile(delete=False, prefix="archlens_upload_")
            tmp.write(self._data)
            tmp.close()
            temp_file = Path(tmp.name)
            archive_path = temp_file

        if archive_size == 0:
            raise EmptyArchiveError("Uploaded archive is empty.")

        if archive_size > limits.max_compressed_bytes:
            archive_mb = archive_size / (1024 * 1024)
            limit_mb = limits.max_compressed_bytes / (1024 * 1024)
            raise LimitExceeded(
                f"Archive is {archive_mb:.1f} MB; the limit is {limit_mb:.0f} MB."
            )

        try:
            # 1. Detect format by magic bytes
            detected_type = detect_archive_type(archive_path)
            if not detected_type:
                raise SourceError(
                    f"Uploaded file '{self.filename}' is not a recognized archive format. "
                    "Expected valid ZIP, TAR, TAR.GZ, or TAR.BZ2 magic bytes."
                )

            await progress(
                JobStatus.EXTRACTING,
                "extracting",
                30.0,
                f"Extracting {detected_type.upper()} archive safely...",
            )

            # 2. Extract with all security defenses active
            extracted_files = safe_extract_archive(archive_path, src_dir, limits)
            skipped_files = getattr(extracted_files, "skipped_files", 0)

            msg = f"Extracted {int(extracted_files)} files from archive"
            if skipped_files > 0:
                msg += f" ({skipped_files} ignored entries skipped)"
            msg += "."

            await progress(
                JobStatus.EXTRACTING,
                "complete",
                100.0,
                msg,
            )

            skipped_by_dir = getattr(extracted_files, "skipped_by_dir", {})
            return {
                "archive_type": detected_type,
                "extracted_files": int(extracted_files),
                "skipped_files": skipped_files,
                "skipped_by_dir": skipped_by_dir,
                "original_filename": self.filename,
            }

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink(missing_ok=True)
            if self._archive_path and self._archive_path.exists() and "archlens_stream_" in self._archive_path.name:
                self._archive_path.unlink(missing_ok=True)
