from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import uuid
from typing import Any, Callable, Protocol

from app.core.config import settings


class JobType(StrEnum):
    REPOSITORY_SYNC = "repository_sync"
    REPOSITORY_INDEX = "repository_index"
    CODE_INDEX = "code_index"
    INITIAL_RHD_REVIEW = "initial_rhd_review"
    ISSUE_INVESTIGATION = "issue_investigation"
    PR_RISK_ANALYSIS = "pr_risk_analysis"
    RELEASE_ANALYSIS = "release_analysis"
    HEALTH_REFRESH = "health_refresh"
    WEEKLY_BRIEF = "weekly_brief"
    WEBHOOK_EVENT_PROCESSING = "webhook_event_processing"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Job:
    job_type: JobType
    repository_id: int | None
    payload: dict[str, Any]
    correlation_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    retries: int = 0
    max_retries: int = settings.job_max_retries
    timeout_seconds: int = settings.job_timeout_seconds
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobQueue(Protocol):
    def enqueue(self, job_type: JobType, repository_id: int | None, payload: dict[str, Any], correlation_id: str | None = None) -> Job:
        ...

    def get(self, job_id: str) -> Job | None:
        ...

    def run_next(self, handlers: dict[JobType, Callable[[Job], Any]]) -> Job | None:
        ...


class LocalJobQueue:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.pending: list[str] = []

    def enqueue(self, job_type: JobType, repository_id: int | None, payload: dict[str, Any], correlation_id: str | None = None) -> Job:
        correlation = correlation_id or f"{job_type}:{repository_id}:{payload}"
        for job in self.jobs.values():
            if job.correlation_id == correlation and job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                return job
        job = Job(job_type=job_type, repository_id=repository_id, payload=payload, correlation_id=correlation)
        self.jobs[job.id] = job
        self.pending.append(job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def run_next(self, handlers: dict[JobType, Callable[[Job], Any]]) -> Job | None:
        if not self.pending:
            return None
        job = self.jobs[self.pending.pop(0)]
        handler = handlers.get(job.job_type)
        if not handler:
            job.status = JobStatus.FAILED
            job.error = "No handler registered"
            job.completed_at = datetime.now(UTC)
            return job
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        try:
            handler(job)
            job.status = JobStatus.COMPLETED
        except Exception as exc:  # pragma: no cover - exercised by callers with concrete handlers
            job.retries += 1
            job.error = str(exc)
            if job.retries <= job.max_retries:
                job.status = JobStatus.QUEUED
                self.pending.append(job.id)
                return job
            job.status = JobStatus.FAILED
        finally:
            if job.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
                job.completed_at = datetime.now(UTC)
        return job
