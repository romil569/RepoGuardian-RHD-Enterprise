from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import AuditLogEvent
from app.db.session import get_db
from app.services.audit import audit_event_dict

router = APIRouter(prefix="/api/audit-log", tags=["audit-log"])


@router.get("")
def list_audit_log(
    repository_id: int | None = None,
    issue_id: int | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = db.query(AuditLogEvent)
    if repository_id is not None:
        query = query.filter(AuditLogEvent.repository_id == repository_id)
    if issue_id is not None:
        query = query.filter(AuditLogEvent.issue_id == issue_id)
    if event_type:
        query = query.filter(AuditLogEvent.event_type == event_type)
    if date_from:
        query = query.filter(AuditLogEvent.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLogEvent.created_at <= date_to)
    total = query.count()
    events = query.order_by(AuditLogEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [audit_event_dict(event) for event in events]}
