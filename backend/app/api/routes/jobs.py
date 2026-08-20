from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import DeploymentJob
from app.db.session import get_db
from app.services.rhd import full_repository_review, initial_scan
from app.services.serverless_jobs import advance_rhd_job, job_payload

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(DeploymentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = job_payload(job, include_result=True)
    if job.status == "COMPLETED" and job.repository_id:
        payload["initial_scan"] = initial_scan(db, job.repository_id)
        payload["review"] = full_repository_review(db, job.repository_id)
    return payload


@router.post("/{job_id}/advance")
def advance_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        payload = advance_rhd_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if payload.get("status") == "COMPLETED" and payload.get("repository_id"):
        repository_id = int(payload["repository_id"])
        payload["initial_scan"] = initial_scan(db, repository_id)
        payload["review"] = full_repository_review(db, repository_id)
    return payload
