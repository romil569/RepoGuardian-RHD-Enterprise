from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.db.models import IncidentInvestigation, Issue, PullRequest, Release, RepositoryEvent
from app.rag.agentic import retrieve_agentic_evidence


def investigate_incident(db: Session, repository_id: int, query: str, persist: bool = True) -> dict[str, object]:
    evidence = retrieve_agentic_evidence(db, repository_id, query, top_k=6)
    timeline = _timeline(db, repository_id, query)
    hypotheses = _hypotheses(query, evidence.get("evidence", []), timeline)
    result = {
        "repository_id": repository_id,
        "query": query,
        "status": "COMPLETED" if evidence.get("evidence") or timeline else "INSUFFICIENT_EVIDENCE",
        "timeline": timeline,
        "hypotheses": hypotheses,
        "evidence_refs": evidence.get("evidence", []),
        "critic": evidence.get("critic", {}),
    }
    if persist:
        row = IncidentInvestigation(repository_id=repository_id, query=query, status=result["status"], hypotheses=hypotheses, timeline=timeline, evidence_refs=result["evidence_refs"])
        db.add(row)
        db.commit()
        result["investigation_id"] = row.id
    return result


def _timeline(db: Session, repository_id: int, query: str) -> list[dict[str, object]]:
    tokens = {token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query.lower())}
    rows: list[dict[str, object]] = []
    for release in db.query(Release).filter_by(repository_id=repository_id).order_by(Release.published_at.desc().nullslast()).limit(8):
        if _matches(tokens, release.tag, release.name or "", release.body or ""):
            rows.append({"type": "release", "timestamp": str(release.published_at), "title": release.tag, "url": release.html_url})
    for pr in db.query(PullRequest).filter_by(repository_id=repository_id).order_by(PullRequest.updated_at.desc().nullslast()).limit(12):
        if _matches(tokens, pr.title, pr.body or ""):
            rows.append({"type": "pull_request", "timestamp": str(pr.updated_at), "title": pr.title, "number": pr.github_pr_number, "url": pr.html_url})
    for issue in db.query(Issue).filter_by(repository_id=repository_id).order_by(Issue.updated_at.desc().nullslast()).limit(12):
        if _matches(tokens, issue.title, issue.body or "", " ".join(issue.labels or [])):
            rows.append({"type": "issue", "timestamp": str(issue.updated_at), "title": issue.title, "number": issue.github_issue_number, "url": issue.html_url})
    for event in db.query(RepositoryEvent).filter_by(repository_id=repository_id).order_by(RepositoryEvent.created_at.desc()).limit(8):
        if _matches(tokens, event.summary, event.event_type):
            rows.append({"type": "event", "timestamp": str(event.created_at), "title": event.summary, "event_type": event.event_type})
    return rows[:12]


def _matches(tokens: set[str], *values: str) -> bool:
    haystack = " ".join(values).lower()
    return any(token in haystack for token in tokens)


def _hypotheses(query: str, evidence_rows: object, timeline: list[dict[str, object]]) -> list[dict[str, object]]:
    evidence_count = len(evidence_rows) if isinstance(evidence_rows, list) else 0
    if not evidence_count and not timeline:
        return [{"hypothesis": "INSUFFICIENT_EVIDENCE", "confidence": "LOW", "evidence_count": 0}]
    text = query.lower()
    kind = "release regression" if any(term in text for term in ["after", "release", "regression"]) else "recent repository change"
    return [
        {
            "hypothesis": f"The incident may correlate with a {kind}; this is correlation, not proof of causation.",
            "confidence": "MEDIUM" if evidence_count >= 3 or len(timeline) >= 3 else "LOW",
            "evidence_count": evidence_count + len(timeline),
        }
    ]
