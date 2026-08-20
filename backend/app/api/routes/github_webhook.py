from __future__ import annotations

import hashlib
import hmac
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Repository, RepositoryEvent
from app.db.session import get_db
from app.platform.queue import JobType
from app.platform.runtime import job_queue

router = APIRouter(prefix="/api/github", tags=["github"])

EVENT_JOB_MAP = {
    "issues": JobType.ISSUE_INVESTIGATION,
    "issue_comment": JobType.ISSUE_INVESTIGATION,
    "pull_request": JobType.PR_RISK_ANALYSIS,
    "pull_request_review": JobType.PR_RISK_ANALYSIS,
    "push": JobType.CODE_INDEX,
    "release": JobType.RELEASE_ANALYSIS,
}


def verify_signature(body: bytes, signature: str | None) -> bool:
    if not settings.github_webhook_secret:
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(settings.github_webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def repository_from_payload(db: Session, payload: dict[str, object]) -> Repository | None:
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        return None
    full_name = repository.get("full_name")
    if not isinstance(full_name, str):
        return None
    return db.query(Repository).filter_by(full_name=full_name).one_or_none()


def event_source(payload: dict[str, object]) -> tuple[str | None, int | None]:
    for source_type in ["issue", "pull_request", "release"]:
        item = payload.get(source_type)
        if isinstance(item, dict):
            source_id = item.get("id")
            return source_type, int(source_id) if isinstance(source_id, int) else None
    return None, None


def normalize_summary(event_type: str, payload: dict[str, object]) -> str:
    action = payload.get("action")
    repo = payload.get("repository")
    full_name = repo.get("full_name") if isinstance(repo, dict) else "unknown repository"
    return f"GitHub {event_type} event {action or 'received'} for {full_name}."


@router.post("/webhooks")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, object]:
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Webhook payload must be a JSON object")
    event_type = x_github_event or "unknown"
    repo = repository_from_payload(db, payload)
    if repo is None:
        return {"status": "accepted_untracked", "event_id": None, "queued_job_id": None, "job_type": None}
    source_type, source_id = event_source(payload)
    event = RepositoryEvent(
        repository_id=repo.id,
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        summary=normalize_summary(event_type, payload),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    job = None
    job_type = EVENT_JOB_MAP.get(event_type)
    if job_type:
        job = job_queue.enqueue(
            job_type,
            repo.id,
            {"event_id": event.id, "github_event": event_type, "delivery_id": x_github_delivery},
            correlation_id=x_github_delivery or str(uuid4()),
        )
    return {"status": "accepted", "event_id": event.id, "queued_job_id": job.id if job else None, "job_type": job.job_type if job else None}


@router.post("/webhook")
async def github_webhook_compat(
    request: Request,
    db: Session = Depends(get_db),
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, object]:
    return await github_webhook(request, db, x_github_event, x_hub_signature_256, x_github_delivery)
