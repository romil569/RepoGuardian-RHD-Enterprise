from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLogEvent

ALLOWED_AUDIT_EVENTS = {
    "REPOSITORY_CONNECTED",
    "REPOSITORY_SYNCED",
    "INVESTIGATION_STARTED",
    "INVESTIGATION_COMPLETED",
    "RECOMMENDATION_CREATED",
    "RECOMMENDATION_APPROVED",
    "RECOMMENDATION_REJECTED",
    "GITHUB_ACTION_EXECUTED",
    "GITHUB_ACTION_FAILED",
    "POLICY_BLOCKED_ACTION",
    "FEEDBACK_SUBMITTED",
    "SETTINGS_CHANGED",
}

SENSITIVE_WORDS = {"token", "secret", "password", "api_key", "authorization", "cookie"}


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        lowered = key.lower()
        if any(word in lowered for word in SENSITIVE_WORDS):
            safe[key] = "[redacted]"
        elif isinstance(value, str) and len(value) > 500:
            safe[key] = value[:500] + "..."
        else:
            safe[key] = value
    return safe


def log_audit_event(
    db: Session,
    event_type: str,
    safe_summary: str,
    *,
    actor: str = "system",
    repository_id: int | None = None,
    issue_id: int | None = None,
    investigation_id: int | None = None,
    action_recommendation_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLogEvent:
    if event_type not in ALLOWED_AUDIT_EVENTS:
        raise ValueError(f"Unsupported audit event type: {event_type}")
    event = AuditLogEvent(
        repository_id=repository_id,
        issue_id=issue_id,
        investigation_id=investigation_id,
        action_recommendation_id=action_recommendation_id,
        actor=actor,
        event_type=event_type,
        safe_summary=safe_summary[:1000],
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(event)
    return event


def audit_event_dict(event: AuditLogEvent) -> dict[str, object]:
    return {
        "id": event.id,
        "repository_id": event.repository_id,
        "issue_id": event.issue_id,
        "investigation_id": event.investigation_id,
        "action_recommendation_id": event.action_recommendation_id,
        "actor": event.actor,
        "event_type": event.event_type,
        "safe_summary": event.safe_summary,
        "metadata": event.metadata_json,
        "created_at": event.created_at,
    }
