from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Repository
from app.db.session import get_db
from app.services.advanced_intelligence import evaluation_metrics, repository_health, weekly_brief

router = APIRouter(prefix="/api/repositories/{repository_id}", tags=["analytics"])


def require_repo(db: Session, repository_id: int) -> Repository:
    repo = db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/health")
def get_health(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    require_repo(db, repository_id)
    return repository_health(db, repository_id)


@router.get("/brief/weekly")
def get_weekly_brief(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    require_repo(db, repository_id)
    return weekly_brief(db, repository_id)


@router.get("/evaluation")
def get_evaluation(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    require_repo(db, repository_id)
    return evaluation_metrics(db, repository_id)
