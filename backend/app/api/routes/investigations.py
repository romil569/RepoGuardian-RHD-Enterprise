from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.tools.analysis import ALLOWED_CLASSIFICATIONS, ALLOWED_ESCALATIONS, ALLOWED_PRIORITIES
from app.db.models import HumanFeedback, Investigation
from app.db.session import get_db
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

ALLOWED_FEEDBACK_TARGETS = {"classification", "priority", "duplicate_recommendation", "escalation_recommendation", "security_signal"}
ALLOWED_FEEDBACK_STATUSES = {"CORRECT", "INCORRECT", "ADJUSTED"}
SECURITY_VALUES = {"LOW_SECURITY_SIGNAL", "POSSIBLE_SECURITY_SENSITIVE", "HIGH_SECURITY_SIGNAL"}
DUPLICATE_VALUES = {"UNLIKELY_DUPLICATE", "POSSIBLE_DUPLICATE", "VERY_LIKELY_DUPLICATE"}


class FeedbackRequest(BaseModel):
    target_type: str
    original_value: str
    feedback_status: str
    corrected_value: str | None = None
    comment: str | None = None


def validate_corrected_value(target_type: str, value: str | None) -> None:
    if value is None:
        return
    allowed = {
        "classification": ALLOWED_CLASSIFICATIONS,
        "priority": ALLOWED_PRIORITIES,
        "duplicate_recommendation": DUPLICATE_VALUES,
        "escalation_recommendation": ALLOWED_ESCALATIONS,
        "security_signal": SECURITY_VALUES,
    }.get(target_type)
    if allowed and value not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid corrected value for {target_type}")


def feedback_dict(item: HumanFeedback) -> dict[str, object]:
    return {
        "id": item.id,
        "repository_id": item.repository_id,
        "issue_id": item.issue_id,
        "investigation_id": item.investigation_id,
        "target_type": item.target_type,
        "original_value": item.original_value,
        "feedback_status": item.feedback_status,
        "corrected_value": item.corrected_value,
        "comment": item.comment,
        "created_at": item.created_at,
    }


@router.post("/{investigation_id}/feedback")
def create_feedback(investigation_id: int, request: FeedbackRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    investigation = db.get(Investigation, investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if request.target_type not in ALLOWED_FEEDBACK_TARGETS:
        raise HTTPException(status_code=422, detail="Invalid feedback target")
    if request.feedback_status not in ALLOWED_FEEDBACK_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid feedback status")
    validate_corrected_value(request.target_type, request.corrected_value)
    feedback = HumanFeedback(
        repository_id=investigation.repository_id,
        issue_id=investigation.issue_id,
        investigation_id=investigation.id,
        target_type=request.target_type,
        original_value=request.original_value,
        feedback_status=request.feedback_status,
        corrected_value=request.corrected_value,
        comment=request.comment,
    )
    db.add(feedback)
    log_audit_event(
        db,
        "FEEDBACK_SUBMITTED",
        f"Feedback submitted for {request.target_type}.",
        actor="local-maintainer",
        repository_id=investigation.repository_id,
        issue_id=investigation.issue_id,
        investigation_id=investigation.id,
        metadata={"target_type": request.target_type, "feedback_status": request.feedback_status},
    )
    db.commit()
    db.refresh(feedback)
    return feedback_dict(feedback)


@router.get("/{investigation_id}/feedback")
def list_feedback(investigation_id: int, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    if not db.get(Investigation, investigation_id):
        raise HTTPException(status_code=404, detail="Investigation not found")
    return [feedback_dict(item) for item in db.query(HumanFeedback).filter_by(investigation_id=investigation_id).order_by(HumanFeedback.id).all()]
