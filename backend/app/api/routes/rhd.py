from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.github.client import GitHubAuthenticationError, GitHubNotFoundError, GitHubServiceError
from app.services.audit import log_audit_event
from app.services.serverless_jobs import create_rhd_onboarding_job
from app.services.sessions import ensure_public_session, record_message, session_context
from app.services.rhd import answer_question, full_repository_review, initial_scan, onboard_repository, parse_repository_input, route_intent

router = APIRouter(prefix="/api/rhd", tags=["rhd"])


class RepositoryInputRequest(BaseModel):
    repository: str
    run_sync: bool = True


class RHDQueryRequest(BaseModel):
    repository_id: int
    question: str
    session_context: dict[str, object] | None = None
    session_id: str | None = None


def handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, GitHubAuthenticationError):
        return HTTPException(status_code=401, detail="GitHub authentication failed")
    if isinstance(exc, GitHubNotFoundError):
        return HTTPException(status_code=404, detail="Repository not found")
    if isinstance(exc, GitHubServiceError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=500, detail="RHD operation failed")


@router.post("/parse-repository")
def parse_repository(request: RepositoryInputRequest) -> dict[str, object]:
    try:
        parsed = parse_repository_input(request.repository)
    except Exception as exc:
        raise handle_error(exc) from exc
    return {"full_name": parsed.full_name, "html_url": parsed.html_url}


@router.post("/onboard")
def onboard(request: RepositoryInputRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result = create_rhd_onboarding_job(db, request.repository, request.run_sync) if settings.is_serverless else onboard_repository(db, request.repository, request.run_sync)
    except Exception as exc:
        raise handle_error(exc) from exc
    repo = result["repository"]
    log_audit_event(
        db,
        "RHD_REPOSITORY_ONBOARDED",
        f"RHD onboarded repository {repo['full_name']} in {result['access_mode']} mode.",
        repository_id=int(repo["id"]),
        metadata={"access_mode": result["access_mode"], "run_sync": request.run_sync},
    )
    db.commit()
    return result


@router.get("/repositories/{repository_id}/initial-scan")
def get_initial_scan(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return initial_scan(db, repository_id)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.get("/repositories/{repository_id}/review")
def get_review(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return full_repository_review(db, repository_id)
    except Exception as exc:
        raise handle_error(exc) from exc


@router.post("/query")
def query(request: RHDQueryRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        session = ensure_public_session(db, request.repository_id, request.session_id or str((request.session_context or {}).get("session_id") or ""))
        context = session_context(session, request.session_context)
        record_message(db, session.id, request.repository_id, "user", request.question)
        result = answer_question(db, request.repository_id, request.question, context)
        record_message(db, session.id, request.repository_id, "assistant", result["answer"], {"intent": result["intent"], "confidence": result["confidence"]})
        result["context"] = session_context(session, result.get("context"))
    except Exception as exc:
        raise handle_error(exc) from exc
    log_audit_event(
        db,
        "RHD_QUERY_ANSWERED",
        f"RHD answered {result['intent']} query.",
        repository_id=request.repository_id,
        metadata={"intent": result["intent"]},
    )
    db.commit()
    return result


@router.get("/intents")
def intents() -> dict[str, object]:
    examples = ["full review", "security", "duplicates", "needs info", "release", "top priorities", "review queue"]
    return {"examples": [{"query": item, "intent": route_intent(item)} for item in examples]}
