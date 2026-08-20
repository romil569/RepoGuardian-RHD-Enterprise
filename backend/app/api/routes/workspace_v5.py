from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.v5_workspace import architecture_artifacts, capability_status, conversation_history, workspace_summary

router = APIRouter(prefix="/api/v5", tags=["rhd-v5-workspace"])


@router.get("/workspace")
def rhd_v5_workspace(db: Session = Depends(get_db)) -> dict[str, object]:
    return workspace_summary(db)


@router.get("/conversations")
def rhd_v5_conversations(limit: int = 20, db: Session = Depends(get_db)) -> dict[str, object]:
    return {"conversations": conversation_history(db, limit=max(1, min(limit, 50)))}


@router.get("/repositories/{repository_id}/architecture")
def rhd_v5_architecture(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return architecture_artifacts(db, repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/capabilities")
def rhd_v5_capabilities() -> dict[str, object]:
    return capability_status()
