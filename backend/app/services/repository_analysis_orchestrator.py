from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ConversationMessage, DeploymentJob, Repository
from app.services.architecture_inference import architecture_payload, generate_architecture_artifacts
from app.services.github_sync import connect_repository
from app.services.rhd import full_repository_review, initial_scan, parse_repository_input, repo_summary, repository_access_mode
from app.services.serverless_jobs import advance_rhd_job, job_payload
from app.services.sessions import ensure_public_session, record_message


def start_repository_analysis(db: Session, repository_input: str, session_id: str | None = None, conversation_id: str | None = None, requested_depth: str = "bounded") -> dict[str, Any]:
    parsed = parse_repository_input(repository_input)
    repo, _created = connect_repository(db, parsed.full_name)
    session = ensure_public_session(db, repo.id, session_id)
    conversation = conversation_id or session.id
    job = DeploymentJob(
        id=str(uuid.uuid4()),
        repository_id=repo.id,
        job_type="v5_repository_analysis",
        payload={
            "repository": repo.full_name,
            "session_id": session.id,
            "conversation_id": conversation,
            "requested_depth": requested_depth,
            "stage_results": {},
        },
        status="QUEUED",
        stage="CONNECT",
        progress=0,
        max_attempts=settings.job_max_retries,
        correlation_id=f"v5-analysis:{repo.id}:{conversation}:{uuid.uuid4()}",
    )
    db.add(job)
    record_message(db, session.id, repo.id, "system", f"RHD started repository analysis for {repo.full_name}.", {"job_id": job.id})
    db.commit()
    db.refresh(job)
    return {
        "analysis_job_id": job.id,
        "job_id": job.id,
        "repository_id": repo.id,
        "conversation_id": conversation,
        "session_id": session.id,
        "status": job.status,
        "repository": repo_summary(db, repo),
        "access_mode": repository_access_mode(repo),
    }


def poll_repository_analysis(db: Session, job_id: str, advance: bool = True) -> dict[str, Any]:
    job = db.get(DeploymentJob, job_id)
    if not job:
        raise ValueError("Job not found")
    if advance and job.status not in {"COMPLETED", "FAILED", "CANCELLED"}:
        payload = advance_rhd_job(db, job_id)
        job = db.get(DeploymentJob, job_id)
    else:
        payload = job_payload(job, include_result=True)
    response = _status_payload(db, job, payload)
    if response["status"] == "COMPLETED" and job.repository_id:
        session_id = str((job.payload or {}).get("session_id") or "")
        already_recorded = (
            db.query(ConversationMessage)
            .filter_by(session_id=session_id, repository_id=job.repository_id, role="assistant")
            .filter(ConversationMessage.metadata_json["job_id"].as_string() == job.id)
            .one_or_none()
            if session_id
            else None
        )
        if session_id and not already_recorded:
            record_message(
                db,
                session_id,
                job.repository_id,
                "assistant",
                f"Repository analysis complete for {response['repository']['full_name']}. Architecture and review are ready.",
                {"job_id": job.id, "artifact_count": len(response.get("available_artifacts", []))},
            )
            db.commit()
    return response


def _status_payload(db: Session, job: DeploymentJob, payload: dict[str, Any]) -> dict[str, Any]:
    stage_results = dict((job.payload or {}).get("stage_results") or {})
    response: dict[str, Any] = {
        "job_id": job.id,
        "status": payload.get("status"),
        "current_stage": payload.get("stage"),
        "stage": payload.get("stage"),
        "progress": payload.get("progress"),
        "message": payload.get("stage_label"),
        "started_at": payload.get("started_at"),
        "updated_at": job.completed_at or job.started_at or job.created_at,
        "error": payload.get("error"),
        "stage_results": stage_results,
        "conversation_id": (job.payload or {}).get("conversation_id"),
        "session_id": (job.payload or {}).get("session_id"),
        "available_artifacts": [],
    }
    if job.repository_id:
        repo = db.get(Repository, job.repository_id)
        if repo:
            response["repository"] = repo_summary(db, repo)
    if job.status == "COMPLETED" and job.repository_id:
        artifacts = architecture_payload(db, job.repository_id)
        if not artifacts.get("artifacts"):
            generate_architecture_artifacts(db, job.repository_id, conversation_id=str((job.payload or {}).get("conversation_id") or ""))
            artifacts = architecture_payload(db, job.repository_id)
        response["available_artifacts"] = artifacts.get("artifacts", [])
        response["architecture"] = artifacts
        response["initial_scan"] = initial_scan(db, job.repository_id)
        response["review"] = full_repository_review(db, job.repository_id)
        source = dict(stage_results.get("source_analysis") or {})
        response["completion_summary"] = {
            "health": response["review"]["executive_assessment"]["state"],
            "architecture": "Generated" if response["available_artifacts"] else "Insufficient evidence",
            "code_analyzed": f"{source.get('files_analyzed', 0)} files / {source.get('symbols_indexed', 0)} symbols",
            "issues_analyzed": response["review"]["issue_backlog"]["total"],
            "prs_analyzed": response["review"]["pr_activity"]["total"],
        }
    return response
