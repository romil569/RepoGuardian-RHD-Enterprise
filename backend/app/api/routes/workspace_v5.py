from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.architecture_inference import architecture_payload, generate_architecture_artifacts
from app.services.repository_analysis_orchestrator import poll_repository_analysis, start_repository_analysis
from app.services.v5_workspace import capability_status, conversation_history, workspace_summary

router = APIRouter(prefix="/api/v5", tags=["rhd-v5-workspace"])


class RepositoryAnalyzeRequest(BaseModel):
    repository: str
    conversation_id: str | None = None
    session_id: str | None = None
    requested_depth: str = "bounded"


@router.get("/workspace")
def rhd_v5_workspace(db: Session = Depends(get_db)) -> dict[str, object]:
    return workspace_summary(db)


@router.get("/conversations")
def rhd_v5_conversations(limit: int = 20, db: Session = Depends(get_db)) -> dict[str, object]:
    return {"conversations": conversation_history(db, limit=max(1, min(limit, 50)))}


@router.post("/repositories/analyze")
def rhd_v5_analyze_repository(request: RepositoryAnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return start_repository_analysis(db, request.repository, request.session_id, request.conversation_id, request.requested_depth)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/jobs/{job_id}")
def rhd_v5_job_status(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return poll_repository_analysis(db, job_id, advance=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/repositories/{repository_id}/architecture")
def rhd_v5_architecture(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        payload = architecture_payload(db, repository_id)
        if not payload.get("artifacts"):
            generate_architecture_artifacts(db, repository_id)
            payload = architecture_payload(db, repository_id)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/capabilities")
def rhd_v5_capabilities() -> dict[str, object]:
    return capability_status()
