from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DeploymentJob, Repository
from app.services.github_sync import connect_repository, sync_repository
from app.services.rhd import full_repository_review, initial_scan, parse_repository_input, repo_summary, repository_access_mode

RHD_ANALYSIS_STAGES = [
    "CONNECT",
    "SYNC_METADATA",
    "SYNC_ISSUES",
    "SYNC_PRS",
    "SYNC_RELEASES",
    "INDEX_DOCUMENTS",
    "RAG_PREP",
    "HEALTH_ANALYSIS",
    "RHD_REVIEW",
    "READY",
]

STAGE_MESSAGES = {
    "CONNECT": "Connecting repository",
    "SYNC_METADATA": "Syncing repository metadata",
    "SYNC_ISSUES": "Syncing issues",
    "SYNC_PRS": "Analyzing pull requests",
    "SYNC_RELEASES": "Reading releases",
    "INDEX_DOCUMENTS": "Building repository intelligence",
    "RAG_PREP": "Preparing RHD review",
    "HEALTH_ANALYSIS": "Validating evidence",
    "RHD_REVIEW": "Preparing final RHD review",
    "READY": "Review ready",
}


def create_rhd_onboarding_job(db: Session, repository_input: str, run_sync: bool) -> dict[str, Any]:
    parsed = parse_repository_input(repository_input)
    repo, created = connect_repository(db, parsed.full_name)
    if not run_sync:
        return {
            "status": "connected",
            "created": created,
            "repository": repo_summary(db, repo),
            "access_mode": repository_access_mode(repo),
            "rhd_status": "READY",
            "initial_scan": initial_scan(db, repo.id),
            "review": full_repository_review(db, repo.id),
        }

    correlation = f"public-rhd-onboard:{repo.id}:{repo.updated_at.isoformat() if repo.updated_at else repo.full_name}"
    existing = db.query(DeploymentJob).filter_by(correlation_id=correlation).one_or_none()
    if existing and existing.status in {"QUEUED", "RUNNING", "COMPLETED"}:
        job = existing
    else:
        job = DeploymentJob(
            id=_new_job_id(),
            repository_id=repo.id,
            job_type="initial_rhd_review",
            payload={"repository": repo.full_name, "run_sync": run_sync, "stage_results": {}},
            status="QUEUED",
            stage="CONNECT",
            progress=0,
            max_attempts=settings.job_max_retries,
            correlation_id=correlation,
        )
        db.add(job)
        db.flush()
    db.commit()
    db.refresh(job)
    return {"status": "JOB_QUEUED", "created": created, "repository": repo_summary(db, repo), "access_mode": repository_access_mode(repo), "job": job_payload(job)}


def _new_job_id() -> str:
    import uuid

    return str(uuid.uuid4())


def job_payload(job: DeploymentJob, include_result: bool = False) -> dict[str, Any]:
    payload = job.payload or {}
    response = {
        "id": job.id,
        "repository_id": job.repository_id,
        "job_type": job.job_type,
        "status": job.status,
        "stage": job.stage,
        "stage_label": STAGE_MESSAGES.get(job.stage or "", job.stage or "Queued"),
        "progress": job.progress,
        "error": job.error,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "bounded_initial_review": bool(payload.get("bounded_initial_review")),
        "stage_results": payload.get("stage_results", {}),
    }
    if include_result and job.status == "COMPLETED" and job.repository_id:
        response["ready"] = True
    return response


def advance_rhd_job(db: Session, job_id: str) -> dict[str, Any]:
    job = db.get(DeploymentJob, job_id)
    if not job:
        raise ValueError("Job not found")
    if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
        return job_payload(job, include_result=True)
    if job.lease_until and job.lease_until > datetime.now(UTC):
        return job_payload(job)

    job.status = "RUNNING"
    job.started_at = job.started_at or datetime.now(UTC)
    job.lease_until = datetime.now(UTC) + timedelta(seconds=settings.job_timeout_seconds)
    job.attempts += 1
    db.commit()
    db.refresh(job)

    try:
        _run_current_stage(db, job)
        job.error = None
        job.lease_until = None
        if job.stage == "READY":
            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = datetime.now(UTC)
        else:
            job.status = "QUEUED"
    except Exception as exc:
        job.error = str(exc)
        job.lease_until = None
        if job.attempts >= job.max_attempts:
            job.status = "FAILED"
            job.completed_at = datetime.now(UTC)
        else:
            job.status = "QUEUED"
    db.commit()
    db.refresh(job)
    return job_payload(job, include_result=True)


def _run_current_stage(db: Session, job: DeploymentJob) -> None:
    current = job.stage or "CONNECT"
    payload = dict(job.payload or {})
    results = dict(payload.get("stage_results") or {})
    repo = db.get(Repository, job.repository_id) if job.repository_id else None
    if not repo:
        repository = str(payload.get("repository") or "")
        repo, _ = connect_repository(db, repository)
        job.repository_id = repo.id

    if current == "SYNC_ISSUES":
        result = sync_repository(db, repo.id)
        results["bounded_sync"] = result
        payload["bounded_initial_review"] = bool(result.get("bounded_initial_review"))
    elif current == "HEALTH_ANALYSIS":
        results["initial_scan"] = initial_scan(db, repo.id)
    elif current == "RHD_REVIEW":
        results["review_generated"] = bool(full_repository_review(db, repo.id))

    current_index = RHD_ANALYSIS_STAGES.index(current) if current in RHD_ANALYSIS_STAGES else 0
    next_index = min(current_index + 1, len(RHD_ANALYSIS_STAGES) - 1)
    job.stage = RHD_ANALYSIS_STAGES[next_index]
    job.progress = int(next_index / (len(RHD_ANALYSIS_STAGES) - 1) * 100)
    payload["stage_results"] = results
    job.payload = payload
