"""Ingestion sources for ArchLens."""

from __future__ import annotations

from ingestion.sources.archive import ArchiveUploadSource
from ingestion.sources.archive_url import ArchiveUrlSource
from ingestion.sources.folder import FolderUploadSource
from ingestion.sources.git import GitSource
from ingestion.sources.local import LocalPathSource
from ingestion.sources.snippet import SnippetSource

__all__ = [
    "ArchiveUploadSource",
    "ArchiveUrlSource",
    "FolderUploadSource",
    "GitSource",
    "LocalPathSource",
    "SnippetSource",
]
