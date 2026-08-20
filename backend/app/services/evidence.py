from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Issue, PullRequest, Release


def verify_evidence_source(db: Session, repository_id: int, source_type: str, source_id: int) -> bool:
    model = {"ISSUE": Issue, "PULL_REQUEST": PullRequest, "RELEASE": Release}.get(source_type)
    if not model:
        return False
    return db.query(model).filter_by(repository_id=repository_id, id=source_id).one_or_none() is not None


def filter_valid_evidence(db: Session, evidence: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    valid: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for item in evidence:
        if verify_evidence_source(db, int(item["repository_id"]), str(item["source_type"]), int(item["source_id"])):
            valid.append(item)
        else:
            rejected.append(item)
    return valid, rejected
