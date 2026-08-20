from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Issue, PullRequest, Release
from app.rag.retriever import search_repository_history

ALLOWED_CLASSIFICATIONS = {
    "BUG",
    "FEATURE_REQUEST",
    "DOCUMENTATION",
    "QUESTION",
    "PERFORMANCE",
    "SECURITY_RELATED",
    "MAINTENANCE",
    "OTHER",
}
ALLOWED_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
ALLOWED_ESCALATIONS = {"NORMAL_QUEUE", "NEEDS_INFORMATION", "POSSIBLE_DUPLICATE", "MAINTAINER_REVIEW", "URGENT_REVIEW"}


def _text(issue: Issue) -> str:
    return f"{issue.title}\n{issue.body or ''}\n{' '.join(issue.labels or [])}".lower()


def classify_issue(issue: Issue) -> dict[str, object]:
    text = _text(issue)
    labels = set(issue.labels or [])
    if "security-review" in labels or "api key" in text or "credential exposure" in text or "secret" in text:
        return {"category": "SECURITY_RELATED", "confidence": 0.93, "explanation": "Security-sensitive wording or labels are present."}
    if "documentation" in labels or "readme" in text or "typo" in text:
        return {"category": "DOCUMENTATION", "confidence": 0.88, "explanation": "The issue is centered on documentation or README text."}
    if "maintenance" in labels or "dependency" in text or "update pytest" in text:
        return {"category": "MAINTENANCE", "confidence": 0.86, "explanation": "The issue asks for dependency or maintenance work."}
    if "enhancement" in labels or "feature" in text or "add " in text:
        return {"category": "FEATURE_REQUEST", "confidence": 0.84, "explanation": "The report requests new product behavior."}
    if "freeze" in text or "slow" in text or "performance" in text:
        return {"category": "PERFORMANCE", "confidence": 0.86, "explanation": "The report describes responsiveness or performance symptoms."}
    if "bug" in labels or "fails" in text or "crash" in text or "stopped working" in text or "not working" in text or "error" in text:
        return {"category": "BUG", "confidence": 0.87, "explanation": "The report describes broken or unexpected behavior."}
    if "?" in issue.title:
        return {"category": "QUESTION", "confidence": 0.68, "explanation": "The title is phrased as a question."}
    return {"category": "OTHER", "confidence": 0.5, "explanation": "No strong controlled category signal was found."}


def check_issue_completeness(issue: Issue, category: str) -> dict[str, object]:
    text = _text(issue)
    required = {
        "BUG": ["steps to reproduce", "expected behavior", "actual behavior", "environment", "version", "error message"],
        "PERFORMANCE": ["steps to reproduce", "environment", "input size", "actual behavior"],
        "SECURITY_RELATED": ["affected area", "impact", "safe example"],
    }.get(category, [])
    signals = {
        "steps to reproduce": any(marker in text for marker in ["steps:", "steps to reproduce", "1."]),
        "expected behavior": "expected" in text,
        "actual behavior": "actual" in text,
        "environment": any(marker in text for marker in ["environment", "windows", "chrome", "edge", "python"]),
        "version": any(marker in text for marker in ["version", "v1.", "v2.", "latest release"]),
        "error message": any(marker in text for marker in ["error", "err_", "message", "logs"]),
        "input size": any(marker in text for marker in ["mb", "large", "size"]),
        "affected area": any(marker in text for marker in ["api key", "credential", "logs", "security"]),
        "impact": any(marker in text for marker in ["exposure", "sensitive", "security", "impact"]),
        "safe example": any(marker in text for marker in ["fictional", "no real secret", "safe"]),
    }
    available = [item for item in required if signals.get(item)]
    missing = [item for item in required if not signals.get(item)]
    if not required:
        return {"score": 85, "available_information": ["clear request"], "missing_information": [], "recommended_follow_up": ""}
    score = int((len(available) / len(required)) * 100)
    follow_up = "Ask for " + ", ".join(missing) + "." if missing else ""
    return {"score": score, "available_information": available, "missing_information": missing, "recommended_follow_up": follow_up}


def calculate_priority(issue: Issue, category: str, duplicate_probability: float, recent_releases: list[Release]) -> dict[str, object]:
    text = _text(issue)
    signals: list[str] = []
    score = 1
    if category == "SECURITY_RELATED":
        score += 3
        signals.append("security-sensitive report")
    if category in {"BUG", "PERFORMANCE"}:
        score += 1
        signals.append("user-impacting defect")
    if "high-priority" in (issue.labels or []):
        score += 1
        signals.append("repository label high-priority")
    if "stopped working" in text or "after v" in text or "after latest" in text:
        score += 1
        signals.append("possible release regression")
    if duplicate_probability >= 0.45:
        score += 1
        signals.append("multiple related reports")
    if recent_releases and any(tag.lower() in text for tag in [release.tag.lower() for release in recent_releases]):
        score += 1
        signals.append("mentions a known recent release")
    if category in {"DOCUMENTATION", "FEATURE_REQUEST", "MAINTENANCE"} and score < 3:
        score = 1
        signals.append("non-urgent issue category")
    if score >= 5:
        level, confidence = "CRITICAL" if category == "SECURITY_RELATED" else "HIGH", 0.86
    elif score >= 3:
        level, confidence = "HIGH", 0.78
    elif score == 2:
        level, confidence = "MEDIUM", 0.72
    else:
        level, confidence = "LOW", 0.75
    return {"level": level, "confidence": confidence, "signals": signals}


def determine_escalation(category: str, completeness_score: int, duplicate_probability: float, priority: str, text: str) -> dict[str, object]:
    reason_codes: list[str] = []
    if completeness_score < 35:
        return {
            "decision": "NEEDS_INFORMATION",
            "confidence": 0.9,
            "reason_codes": ["INSUFFICIENT_INFORMATION"],
            "recommended_action": "Ask the reporter for reproduction steps, environment, version, and error details.",
        }
    if duplicate_probability >= 0.55:
        return {
            "decision": "POSSIBLE_DUPLICATE",
            "confidence": 0.84,
            "reason_codes": ["LIKELY_DUPLICATE", "MULTIPLE_RELATED_REPORTS"],
            "recommended_action": "Review similar issues before triaging independently.",
        }
    if category == "SECURITY_RELATED":
        return {
            "decision": "URGENT_REVIEW",
            "confidence": 0.92,
            "reason_codes": ["SECURITY_SENSITIVE"],
            "recommended_action": "Escalate to a maintainer for private security-aware review.",
        }
    if priority in {"HIGH", "CRITICAL"}:
        reason_codes.append("HIGH_USER_IMPACT")
        if "after v" in text or "after latest" in text or "stopped working" in text:
            reason_codes.append("POSSIBLE_REGRESSION")
        return {
            "decision": "MAINTAINER_REVIEW",
            "confidence": 0.82,
            "reason_codes": reason_codes,
            "recommended_action": "Route to maintainer review with linked repository evidence.",
        }
    return {
        "decision": "NORMAL_QUEUE",
        "confidence": 0.73,
        "reason_codes": [],
        "recommended_action": "Keep in normal triage queue.",
    }


def get_recent_releases(db: Session, repository_id: int, limit: int = 3) -> list[Release]:
    return db.query(Release).filter_by(repository_id=repository_id).order_by(Release.published_at.desc().nullslast()).limit(limit).all()


def get_related_pull_requests(db: Session, repository_id: int, query: str, limit: int = 3) -> list[PullRequest]:
    tokens = [token for token in query.lower().split() if len(token) > 3][:6]
    prs = db.query(PullRequest).filter_by(repository_id=repository_id).all()
    scored = []
    for pr in prs:
        haystack = f"{pr.title} {pr.body or ''}".lower()
        hits = sum(1 for token in tokens if token in haystack)
        if hits:
            scored.append((hits, pr))
    return [pr for _, pr in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def search_similar_issues(db: Session, repository_id: int, issue: Issue, limit: int = 3) -> list[dict[str, object]]:
    results = search_repository_history(db, repository_id, f"{issue.title}\n{issue.body or ''}", top_k=limit + 3)
    return [
        {
            "source_type": result.source_type,
            "source_id": result.source_id,
            "github_number": result.github_number,
            "title": result.title,
            "source_url": result.source_url,
            "relevance_score": result.relevance_score,
        }
        for result in results
        if not (result.source_type == "ISSUE" and result.source_id == issue.id)
    ][:limit]
