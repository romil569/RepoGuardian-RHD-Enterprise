from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import ActionRecommendation, Investigation
from app.db.session import get_db
from app.core.config import settings
from app.services.action_recommendations import (
    ActionWorkflowError,
    approve_recommendation,
    execute_recommendation,
    recommendation_dict,
    reject_recommendation,
    validate_policy,
)

router = APIRouter(tags=["action-recommendations"])


class ActorRequest(BaseModel):
    actor: str = "local-maintainer"


class RejectRequest(ActorRequest):
    reason: str | None = None


def require_recommendation(db: Session, recommendation_id: int) -> ActionRecommendation:
    recommendation = db.get(ActionRecommendation, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Action recommendation not found")
    return recommendation


@router.get("/api/review-queue")
def review_queue(
    filter: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    query = db.query(ActionRecommendation).join(Investigation)
    if filter == "PENDING":
        query = query.filter(ActionRecommendation.status == "PENDING")
    elif filter == "URGENT":
        query = query.filter(Investigation.escalation_decision.in_(["URGENT_REVIEW", "MAINTAINER_REVIEW"]))
    elif filter == "SECURITY":
        query = query.filter(ActionRecommendation.action_type == "ESCALATE_FOR_SECURITY_REVIEW")
    elif filter == "POSSIBLE_DUPLICATE":
        query = query.filter(ActionRecommendation.action_type == "MARK_AS_POSSIBLE_DUPLICATE")
    elif filter == "NEEDS_INFORMATION":
        query = query.filter(ActionRecommendation.action_type == "REQUEST_MORE_INFORMATION")
    elif filter == "HIGH_PRIORITY":
        query = query.filter(Investigation.priority.in_(["HIGH", "CRITICAL"]))
    elif filter == "FAILED_ACTIONS":
        query = query.filter(ActionRecommendation.status == "FAILED")
    return [recommendation_dict(item) for item in query.order_by(ActionRecommendation.created_at.desc()).limit(limit).all()]


@router.get("/api/action-recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    recommendation = require_recommendation(db, recommendation_id)
    result = recommendation_dict(recommendation)
    policy = validate_policy(db, recommendation)
    result["policy_validation"] = {"decision": policy.decision, "reason": policy.reason}
    return result


@router.post("/api/action-recommendations/{recommendation_id}/approve")
def approve(recommendation_id: int, request: ActorRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if settings.public_analysis_mode and not settings.enable_public_write_actions:
        raise HTTPException(status_code=403, detail="Public deployment is read-only; action approval is disabled")
    recommendation = require_recommendation(db, recommendation_id)
    try:
        approve_recommendation(db, recommendation, request.actor)
    except ActionWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(recommendation)
    return recommendation_dict(recommendation)


@router.post("/api/action-recommendations/{recommendation_id}/reject")
def reject(recommendation_id: int, request: RejectRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if settings.public_analysis_mode and not settings.enable_public_write_actions:
        raise HTTPException(status_code=403, detail="Public deployment is read-only; action rejection is disabled")
    recommendation = require_recommendation(db, recommendation_id)
    try:
        reject_recommendation(db, recommendation, request.actor, request.reason)
    except ActionWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(recommendation)
    return recommendation_dict(recommendation)


@router.post("/api/action-recommendations/{recommendation_id}/execute")
def execute(recommendation_id: int, request: ActorRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if settings.public_analysis_mode and not settings.enable_public_write_actions:
        raise HTTPException(status_code=403, detail="Public deployment is read-only; external GitHub writes are disabled")
    recommendation = require_recommendation(db, recommendation_id)
    try:
        execute_recommendation(db, recommendation, actor=request.actor)
    except ActionWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(recommendation)
    return recommendation_dict(recommendation)
