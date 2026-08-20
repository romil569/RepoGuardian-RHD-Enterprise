from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.workflows.investigation import InvestigationOrchestrator
from app.api.routes.repositories import issue_dict
from app.db.models import Issue
from app.db.session import get_db

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.get("/{issue_id}")
def get_issue(issue_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue_dict(issue)


@router.post("/{issue_id}/investigate")
def investigate_issue(issue_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return InvestigationOrchestrator(db).investigate_issue(issue_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
