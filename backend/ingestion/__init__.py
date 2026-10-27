"""ArchLens universal ingestion layer.

Provides source-agnostic workspace preparation, language detection,
security validation (SSRF, Zip Slip, Zip Bomb), and parallel pipeline orchestration.
"""

from __future__ import annotations

from ingestion.config import IngestionLimits
from ingestion.exceptions import (
    AuthError,
    IngestionError,
    JobNotFoundError,
    LimitExceeded,
    LocalPathDisabledError,
    NoSupportedFilesError,
    SecurityError,
    SourceError,
    ZipBombError,
)
from ingestion.job_store import JobRecord, JobStore, default_job_store
from ingestion.language_detector import scan_workspace
from ingestion.models import (
    IngestionSource,
    JobEvent,
    JobStatus,
    ProgressReporter,
    WorkspaceMetadata,
)
from ingestion.orchestrator import IngestionOrchestrator, default_orchestrator
from ingestion.security import (
    detect_archive_type,
    is_safe_path,
    safe_download_url,
    safe_extract_archive,
    validate_safe_url,
)
from ingestion.sources import (
    ArchiveUploadSource,
    ArchiveUrlSource,
    FolderUploadSource,
    GitSource,
    LocalPathSource,
    SnippetSource,
)
from ingestion.workspace import Workspace, WorkspaceManager

__all__ = [
    "ArchiveUploadSource",
    "ArchiveUrlSource",
    "AuthError",
    "FolderUploadSource",
    "GitSource",
    "IngestionError",
    "IngestionLimits",
    "IngestionOrchestrator",
    "IngestionSource",
    "JobEvent",
    "JobNotFoundError",
    "JobRecord",
    "JobStatus",
    "JobStore",
    "LimitExceeded",
    "LocalPathDisabledError",
    "LocalPathSource",
    "NoSupportedFilesError",
    "ProgressReporter",
    "SecurityError",
    "SnippetSource",
    "SourceError",
    "Workspace",
    "WorkspaceManager",
    "WorkspaceMetadata",
    "ZipBombError",
    "default_job_store",
    "default_orchestrator",
    "detect_archive_type",
    "is_safe_path",
    "safe_download_url",
    "safe_extract_archive",
    "scan_workspace",
    "validate_safe_url",
]
