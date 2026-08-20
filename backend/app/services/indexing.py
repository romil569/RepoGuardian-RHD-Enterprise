from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Comment, IndexedDocument, Issue, PullRequest, Release
from app.services.text import vectorize


def _upsert_document(
    db: Session,
    *,
    repository_id: int,
    source_type: str,
    source_id: int,
    github_number: int | None,
    title: str,
    source_url: str | None,
    text: str,
    created_at,
    updated_at,
) -> None:
    existing = (
        db.query(IndexedDocument)
        .filter_by(repository_id=repository_id, source_type=source_type, source_id=source_id)
        .one_or_none()
    )
    data = {
        "repository_id": repository_id,
        "source_type": source_type,
        "source_id": source_id,
        "github_number": github_number,
        "title": title,
        "source_url": source_url,
        "text": text,
        "token_vector": vectorize(f"{title}\n{text}"),
        "created_at": created_at,
        "updated_at": updated_at,
        "indexed_at": datetime.now(UTC),
    }
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        db.add(IndexedDocument(**data))


def index_repository(db: Session, repository_id: int) -> int:
    db.execute(delete(IndexedDocument).where(IndexedDocument.repository_id == repository_id))
    count = 0
    for issue in db.query(Issue).filter_by(repository_id=repository_id).all():
        comments = db.query(Comment).filter_by(repository_id=repository_id, issue_id=issue.id).all()
        comment_text = "\n\n".join(comment.body or "" for comment in comments)
        body = "\n\n".join(part for part in [issue.body or "", comment_text] if part)
        _upsert_document(
            db,
            repository_id=repository_id,
            source_type="ISSUE",
            source_id=issue.id,
            github_number=issue.github_issue_number,
            title=issue.title,
            source_url=issue.html_url,
            text=body,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )
        count += 1
    for pr in db.query(PullRequest).filter_by(repository_id=repository_id).all():
        _upsert_document(
            db,
            repository_id=repository_id,
            source_type="PULL_REQUEST",
            source_id=pr.id,
            github_number=pr.github_pr_number,
            title=pr.title,
            source_url=pr.html_url,
            text=pr.body or "",
            created_at=pr.created_at,
            updated_at=pr.updated_at,
        )
        count += 1
    for release in db.query(Release).filter_by(repository_id=repository_id).all():
        _upsert_document(
            db,
            repository_id=repository_id,
            source_type="RELEASE",
            source_id=release.id,
            github_number=None,
            title=release.name or release.tag,
            source_url=release.html_url,
            text=release.body or "",
            created_at=release.published_at,
            updated_at=release.last_synced_at,
        )
        count += 1
    db.commit()
    return count
