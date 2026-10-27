"""Direct archive URL ingestion source.

Supports:
- Downloading an archive (.zip, .tar.gz, etc.) from an HTTPS URL
- SSRF validation and redirect tracking
- Stream download with size cap and timeout
- Magic bytes detection and secure extraction
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ingestion.config import IngestionLimits
from ingestion.hash_utils import hash_archive_url
from ingestion.models import IngestionSource, JobStatus, ProgressReporter
from ingestion.security import safe_download_url, safe_extract_archive

logger = logging.getLogger(__name__)


class ArchiveUrlSource(IngestionSource):
    """Downloads an archive from a URL and extracts it into the workspace."""

    def __init__(self, url: str) -> None:
        self.url = url.strip()

    @property
    def source_type(self) -> str:
        return "archive_url"

    @property
    def display_name(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.netloc}{parsed.path}"

    @property
    def repo_name(self) -> str:
        parsed = urlparse(self.url)
        filename = Path(parsed.path).name
        for ext in (".tar.gz", ".tar.bz2", ".tgz", ".zip", ".tar"):
            if filename.lower().endswith(ext):
                filename = filename[: -len(ext)]
                break
        return filename or "archive"

    @property
    def source_hash(self) -> str:
        return hash_archive_url(self.url)

    async def fetch(
        self,
        src_dir: Path,
        limits: IngestionLimits,
        progress: ProgressReporter,
    ) -> dict[str, Any]:
        await progress(JobStatus.FETCHING, "downloading", 10.0, f"Downloading archive from {self.display_name}")

        temp_fd, temp_name = tempfile.mkstemp(prefix="archlens_download_")
        import os

        os.close(temp_fd)
        temp_archive = Path(temp_name)
        try:
            # 1. Download safely with SSRF and redirect validation
            downloaded_bytes = await safe_download_url(self.url, temp_archive, limits)

            await progress(
                JobStatus.EXTRACTING,
                "extracting",
                50.0,
                f"Downloaded {downloaded_bytes} bytes. Extracting archive...",
            )

            # 2. Extract safely
            extracted_files = safe_extract_archive(temp_archive, src_dir, limits)

            await progress(
                JobStatus.EXTRACTING,
                "complete",
                100.0,
                f"Extracted {extracted_files} files.",
            )

            return {
                "downloaded_bytes": downloaded_bytes,
                "extracted_files": extracted_files,
                "url": self.url,
            }

        finally:
            if temp_archive.exists():
                temp_archive.unlink(missing_ok=True)
