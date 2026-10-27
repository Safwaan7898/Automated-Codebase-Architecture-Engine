"""Custom exception hierarchy for the ingestion layer.

All exceptions are user-facing: the message should be clear and actionable.
"""

from __future__ import annotations


class IngestionError(Exception):
    """Base class for all ingestion errors."""

    status_code: int = 500
    user_message: str = "An unexpected error occurred during ingestion."

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_message = message


class SecurityError(IngestionError):
    """Raised when a security violation is detected.

    Examples: zip slip, path traversal, symlink escape, SSRF.
    """

    status_code = 422


class ZipBombError(SecurityError):
    """Archive exceeds bomb-detection thresholds."""

    status_code = 422


class LimitExceeded(IngestionError):
    """A configurable resource limit was exceeded."""

    status_code = 413


class SourceError(IngestionError):
    """Source is unavailable or invalid (bad URL, corrupt archive, etc.)."""

    status_code = 400


class EmptyArchiveError(SourceError):
    """Archive is empty or contains no files."""

    status_code = 422


class AuthError(IngestionError):
    """Authentication/authorisation required or failed."""

    status_code = 401


class LocalPathDisabledError(IngestionError):
    """Local path ingestion is disabled in this deployment."""

    status_code = 403

    def __init__(self) -> None:
        super().__init__("Local path ingestion is disabled. Set ARCHLENS_ALLOW_LOCAL_PATHS=true to enable it.")


class NoSupportedFilesError(IngestionError):
    """Workspace contains no files in a supported language."""

    status_code = 422


class JobNotFoundError(IngestionError):
    """Requested job_id does not exist."""

    status_code = 404
