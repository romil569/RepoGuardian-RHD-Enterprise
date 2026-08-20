from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import IndexedDocument
from app.services.text import cosine, snippet, vectorize


@dataclass(frozen=True)
class SearchResult:
    repository_id: int
    source_type: str
    source_id: int
    github_number: int | None
    title: str
    snippet: str
    source_url: str | None
    relevance_score: float


def search_repository_history(db: Session, repository_id: int, query: str, top_k: int = 5) -> list[SearchResult]:
    query_vector = vectorize(query)
    # Repository filtering happens in the database query, before scoring.
    docs = db.query(IndexedDocument).filter(IndexedDocument.repository_id == repository_id).all()
    scored: list[SearchResult] = []
    for doc in docs:
        semantic = cosine(query_vector, doc.token_vector or {})
        keyword_hits = sum(1 for token in query_vector if token in (doc.text or "").lower() or token in doc.title.lower())
        score = semantic + min(keyword_hits * 0.05, 0.25)
        if score > 0:
            scored.append(
                SearchResult(
                    repository_id=doc.repository_id,
                    source_type=doc.source_type,
                    source_id=doc.source_id,
                    github_number=doc.github_number,
                    title=doc.title,
                    snippet=snippet(doc.text or doc.title, query),
                    source_url=doc.source_url,
                    relevance_score=round(float(score), 4),
                )
            )
    return sorted(scored, key=lambda item: item.relevance_score, reverse=True)[:top_k]
