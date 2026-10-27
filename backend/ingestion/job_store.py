"""In-memory job tracking, WebSocket event publishing, and deduplication cache."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ingestion.models import JobEvent, JobStatus, WorkspaceMetadata

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    source_hash: str = ""
    metadata: WorkspaceMetadata | None = None
    result: Any | None = None
    analysis: Any | None = None
    error: str | None = None
    events: list[JobEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    _subscribers: list[asyncio.Queue[JobEvent]] = field(default_factory=list)

    def add_subscriber(self) -> asyncio.Queue[JobEvent]:
        q: asyncio.Queue[JobEvent] = asyncio.Queue()
        # Replay past events to the new subscriber
        for ev in self.events:
            q.put_nowait(ev)
        self._subscribers.append(q)
        return q

    def remove_subscriber(self, q: asyncio.Queue[JobEvent]) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def emit(self, event: JobEvent) -> None:
        self.events.append(event)
        self.status = event.status
        if event.metadata:
            self.metadata = event.metadata
        if event.error:
            self.error = event.error

        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except Exception:
                dead_queues.append(q)
        for q in dead_queues:
            self.remove_subscriber(q)


class JobStore:
    """Singleton-style or injectable store for ingestion jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        # source_hash -> job_id
        self._hash_to_job: dict[str, str] = {}
        # commit_hash -> job_id
        self._commit_to_job: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def find_cached_job(self, source_hash: str) -> JobRecord | None:
        """Find a previously completed job with the exact same source hash."""
        job_id = self._hash_to_job.get(source_hash)
        if job_id:
            record = self._jobs.get(job_id)
            if record and record.status == JobStatus.COMPLETE and (record.result or record.analysis):
                return record
        return None

    def find_cached_by_commit(self, commit_hash: str) -> JobRecord | None:
        """Find a previously completed job with the exact same git commit hash."""
        if not commit_hash:
            return None
        job_id = self._commit_to_job.get(commit_hash)
        if job_id:
            record = self._jobs.get(job_id)
            if record and record.status == JobStatus.COMPLETE and (record.result or record.analysis):
                return record
        return None

    def create_job(self, job_id: str, source_hash: str) -> JobRecord:
        record = JobRecord(job_id=job_id, source_hash=source_hash)
        self._jobs[job_id] = record
        if source_hash:
            self._hash_to_job[source_hash] = job_id
        return record

    def record_commit(self, job_id: str, commit_hash: str) -> None:
        if commit_hash:
            self._commit_to_job[commit_hash] = job_id

    async def stream_events(self, job_id: str) -> AsyncIterator[JobEvent]:
        record = self.get_job(job_id)
        if not record:
            return

        queue = record.add_subscriber()
        try:
            while True:
                event = await queue.get()
                yield event
                if event.status in (JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED):
                    break
        finally:
            record.remove_subscriber(queue)


# Global default store instance
default_job_store = JobStore()
