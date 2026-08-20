from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import uuid
from typing import Any, Callable, Protocol

from app.core.config import settings
from app.db.models import DeploymentJob
from app.db.session import SessionLocal


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
    progress: int = 0
    stage: str | None = None


def _job_from_row(row: DeploymentJob) -> Job:
    return Job(
        id=row.id,
        job_type=JobType(row.job_type),
        repository_id=row.repository_id,
        payload=row.payload or {},
        correlation_id=row.correlation_id,
        status=JobStatus(row.status),
        retries=row.attempts,
        max_retries=row.max_attempts,
        error=row.error,
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        progress=row.progress,
        stage=row.stage,
    )


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


class PostgresJobQueue:
    def enqueue(self, job_type: JobType, repository_id: int | None, payload: dict[str, Any], correlation_id: str | None = None) -> Job:
        correlation = correlation_id or f"{job_type}:{repository_id}:{payload}"
        db = SessionLocal()
        try:
            existing = db.query(DeploymentJob).filter_by(correlation_id=correlation).one_or_none()
            if existing and existing.status in {JobStatus.QUEUED.value, JobStatus.RUNNING.value}:
                return _job_from_row(existing)
            row = DeploymentJob(
                id=str(uuid.uuid4()),
                job_type=job_type.value,
                repository_id=repository_id,
                payload=payload,
                status=JobStatus.QUEUED.value,
                stage=str(payload.get("stage") or "CONNECT"),
                progress=int(payload.get("progress") or 0),
                max_attempts=settings.job_max_retries,
                correlation_id=correlation,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _job_from_row(row)
        finally:
            db.close()

    def get(self, job_id: str) -> Job | None:
        db = SessionLocal()
        try:
            row = db.get(DeploymentJob, job_id)
            return _job_from_row(row) if row else None
        finally:
            db.close()

    def run_next(self, handlers: dict[JobType, Callable[[Job], Any]]) -> Job | None:
        db = SessionLocal()
        try:
            now = datetime.now(UTC)
            row = (
                db.query(DeploymentJob)
                .filter(DeploymentJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]))
                .filter((DeploymentJob.lease_until.is_(None)) | (DeploymentJob.lease_until < now))
                .order_by(DeploymentJob.created_at)
                .with_for_update(skip_locked=True)
                .first()
            )
            if not row:
                return None
            row.status = JobStatus.RUNNING.value
            row.started_at = row.started_at or now
            row.lease_until = now + timedelta(seconds=settings.job_timeout_seconds)
            row.attempts += 1
            db.commit()
            job = _job_from_row(row)
        finally:
            db.close()

        handler = handlers.get(job.job_type)
        db = SessionLocal()
        try:
            row = db.get(DeploymentJob, job.id)
            if not row:
                return job
            if not handler:
                row.status = JobStatus.FAILED.value
                row.error = "No handler registered"
                row.completed_at = datetime.now(UTC)
                db.commit()
                db.refresh(row)
                return _job_from_row(row)
            try:
                handler(job)
                row.status = JobStatus.COMPLETED.value
                row.progress = max(row.progress, 100)
                row.completed_at = datetime.now(UTC)
                row.error = None
            except Exception as exc:  # pragma: no cover - concrete callers cover behavior
                row.error = str(exc)
                if row.attempts < row.max_attempts:
                    row.status = JobStatus.QUEUED.value
                    row.lease_until = None
                else:
                    row.status = JobStatus.FAILED.value
                    row.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(row)
            return _job_from_row(row)
        finally:
            db.close()


class RedisJobQueue:
    def __init__(self) -> None:
        self.fallback = LocalJobQueue()

    def enqueue(self, job_type: JobType, repository_id: int | None, payload: dict[str, Any], correlation_id: str | None = None) -> Job:
        return self.fallback.enqueue(job_type, repository_id, payload, correlation_id)

    def get(self, job_id: str) -> Job | None:
        return self.fallback.get(job_id)

    def run_next(self, handlers: dict[JobType, Callable[[Job], Any]]) -> Job | None:
        return self.fallback.run_next(handlers)


def create_job_queue() -> JobQueue:
    if settings.queue_backend == "redis" and settings.redis_url:
        return RedisJobQueue()
    if settings.queue_backend == "postgres" and settings.database_url.startswith(("postgresql://", "postgresql+")):
        return PostgresJobQueue()
    return LocalJobQueue()
