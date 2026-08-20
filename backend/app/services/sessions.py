from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ConversationMessage, PublicSession


def ensure_public_session(db: Session, repository_id: int, session_id: str | None = None) -> PublicSession:
    if session_id:
        existing = db.get(PublicSession, session_id)
        if existing and existing.repository_id == repository_id:
            return existing
    session = PublicSession(id=str(uuid.uuid4()), repository_id=repository_id, metadata_json={})
    db.add(session)
    db.flush()
    return session


def record_message(db: Session, session_id: str, repository_id: int, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
    db.add(
        ConversationMessage(
            session_id=session_id,
            repository_id=repository_id,
            role=role,
            content=content,
            metadata_json=metadata or {},
        )
    )


def session_context(session: PublicSession, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(session.metadata_json or {})
    context["session_id"] = session.id
    context["repository_id"] = session.repository_id
    if extra:
        context.update(extra)
    session.metadata_json = context
    return context
