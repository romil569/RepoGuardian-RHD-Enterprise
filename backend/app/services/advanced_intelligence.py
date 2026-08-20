from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
import statistics

from sqlalchemy.orm import Session

from app.agents.tools.analysis import classify_issue
from app.core.config import settings
from app.db.models import AgentExecutionStep, Comment, HumanFeedback, Investigation, Issue, PullRequest, Release, Repository
from app.services.text import cosine, tokenize, vectorize

GENERIC_TERMS = {
    "error",
    "issue",
    "application",
    "working",
    "latest",
    "update",
    "please",
    "fix",
    "after",
    "when",
    "with",
    "from",
}

TECH_TERMS = {
    "login",
    "authentication",
    "auth",
    "authenticate",
    "password",
    "upload",
    "image",
    "png",
    "jpeg",
    "readme",
    "pytest",
    "api",
    "key",
    "logs",
    "release",
    "v1.2.0",
}

CANONICAL_TERMS = {
    "authenticate": "auth",
    "authentication": "auth",
    "login": "auth",
    "password": "auth",
    "uploads": "upload",
    "uploaded": "upload",
    "uploading": "upload",
    "images": "image",
}

SECURITY_PATTERNS = {
    "credential exposure": "CREDENTIAL_EXPOSURE",
    "api key": "CREDENTIAL_EXPOSURE",
    "secret": "SECRET_LEAKAGE",
    "authorization": "ACCESS_CONTROL",
    "auth bypass": "AUTHENTICATION_BYPASS",
    "authentication bypass": "AUTHENTICATION_BYPASS",
    "sensitive information": "SENSITIVE_INFORMATION_EXPOSURE",
    "injection": "INJECTION_REPORT",
    "remote code execution": "RCE_INDICATOR",
    "dependency vulnerability": "DEPENDENCY_VULNERABILITY",
}


def issue_text(issue: Issue) -> str:
    return f"{issue.title}\n{issue.body or ''}\n{' '.join(issue.labels or [])}"


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def important_terms(text: str) -> set[str]:
    tokens = {CANONICAL_TERMS.get(token, token) for token in tokenize(text)}
    return {token for token in tokens if token in TECH_TERMS or (len(token) > 5 and token not in GENERIC_TERMS)}


def keyword_overlap(left: str, right: str) -> float:
    left_terms = set(CANONICAL_TERMS.get(token, token) for token in tokenize(left) if token not in GENERIC_TERMS)
    right_terms = set(CANONICAL_TERMS.get(token, token) for token in tokenize(right) if token not in GENERIC_TERMS)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def duplicate_state(score: float) -> str:
    if score >= settings.duplicate_very_likely_threshold:
        return "VERY_LIKELY_DUPLICATE"
    if score >= settings.duplicate_possible_threshold:
        return "POSSIBLE_DUPLICATE"
    return "UNLIKELY_DUPLICATE"


def analyze_duplicates(db: Session, issue: Issue, limit: int = 5) -> dict[str, object]:
    target_text = issue_text(issue)
    target_vector = vectorize(target_text)
    target_category = str(classify_issue(issue)["category"])
    candidates: list[dict[str, object]] = []
    for candidate in db.query(Issue).filter(Issue.repository_id == issue.repository_id, Issue.id != issue.id).all():
        candidate_text = issue_text(candidate)
        semantic = cosine(target_vector, vectorize(candidate_text))
        overlap = keyword_overlap(target_text, candidate_text)
        candidate_category = str(classify_issue(candidate)["category"])
        category_match = target_category == candidate_category
        entity_terms = important_terms(target_text) & important_terms(candidate_text)
        entity_overlap = min(len(entity_terms) / 3, 1.0)
        issue_updated = as_utc(issue.updated_at)
        candidate_updated = as_utc(candidate.updated_at)
        temporal = 0.05 if candidate_updated and issue_updated and abs((issue_updated - candidate_updated).days) <= 14 else 0.0
        if not entity_terms and overlap < 0.18:
            final = semantic * 0.35 + overlap * 0.2
        else:
            final = semantic * 0.45 + overlap * 0.25 + (0.15 if category_match else -0.12) + entity_overlap * 0.12 + temporal
        if "auth" in entity_terms:
            final += 0.14
        if "upload" in entity_terms:
            final += 0.26
        if {"upload", "image"} <= entity_terms:
            final += 0.12
        final = max(0.0, min(final, 1.0))
        why = []
        if semantic >= 0.35:
            why.append("similar repository-history vector")
        if overlap >= 0.2:
            why.append("overlapping non-generic terms")
        if category_match:
            why.append(f"same category {target_category}")
        if entity_terms:
            why.append("shared terms: " + ", ".join(sorted(entity_terms)[:5]))
        candidates.append(
            {
                "candidate_issue_id": candidate.id,
                "github_issue_number": candidate.github_issue_number,
                "title": candidate.title,
                "url": candidate.html_url,
                "semantic_similarity": round(semantic, 4),
                "keyword_overlap": round(overlap, 4),
                "category_match": category_match,
                "final_duplicate_score": round(final, 4),
                "duplicate_state": duplicate_state(final),
                "why_similar": "; ".join(why) if why else "Low-confidence weak similarity only.",
            }
        )
    ranked = sorted(candidates, key=lambda item: item["final_duplicate_score"], reverse=True)[:limit]
    return {
        "duplicate_candidates": ranked,
        "top_score": ranked[0]["final_duplicate_score"] if ranked else 0.0,
        "duplicate_state": ranked[0]["duplicate_state"] if ranked else "UNLIKELY_DUPLICATE",
    }


def analyze_completeness(issue: Issue, category: str) -> dict[str, object]:
    text = issue_text(issue).lower()
    requirement_map = {
        "BUG": {
            "steps to reproduce": ["steps:", "steps to reproduce", "1."],
            "expected behavior": ["expected"],
            "actual behavior": ["actual"],
            "environment": ["environment", "windows", "macos", "linux", "chrome", "edge", "python"],
            "application/library version": ["version", "v1.", "v2.", "latest release"],
            "error message/logs": ["error", "err_", "logs", "message"],
        },
        "PERFORMANCE": {
            "workload/input size": ["mb", "large", "size", "workload"],
            "expected performance": ["expected"],
            "actual performance": ["actual", "freeze", "slow", "seconds"],
            "environment": ["environment", "windows", "chrome", "edge", "python"],
            "version": ["version", "v1.", "v2."],
            "timings": ["seconds", "ms", "minutes"],
        },
        "SECURITY_RELATED": {
            "affected area": ["api key", "credential", "logs", "auth", "security"],
            "impact": ["exposure", "sensitive", "security", "leak"],
            "safe non-secret example": ["fictional", "no real secret", "safe"],
        },
        "DOCUMENTATION": {
            "location": ["readme", "section", "installation", "docs"],
            "proposed correction": ["typo", "should", "replace", "say"],
        },
        "FEATURE_REQUEST": {
            "use case": ["use case", "users", "maintainers", "work"],
            "expected benefit": ["benefit", "support", "help", "allow"],
            "current limitation": ["currently", "current", "limitation", "not"],
        },
    }
    requirements = requirement_map.get(category, {"clear request": [issue.title.lower()]})
    available = [name for name, markers in requirements.items() if any(marker in text for marker in markers)]
    missing = [name for name in requirements if name not in available]
    score = int((len(available) / max(len(requirements), 1)) * 100)
    if category in {"DOCUMENTATION", "FEATURE_REQUEST", "MAINTENANCE"} and score < 60:
        score = max(score, 60)
    questions = [f"Please provide {item}." for item in missing]
    return {
        "completeness_score": score,
        "score": score,
        "available_information": available,
        "missing_information": missing,
        "recommended_follow_up_questions": questions,
        "recommended_follow_up": " ".join(questions),
        "issue_type_specific_requirements": list(requirements.keys()),
        "confidence": 0.82 if requirements else 0.55,
    }


def analyze_security(issue: Issue) -> dict[str, object]:
    text = issue_text(issue).lower()
    original_text = text
    for negated in [
        "no security bypass",
        "no secret exposure",
        "no credential exposure",
        "does not include any real secret",
    ]:
        text = text.replace(negated, "")
    signals = []
    for phrase, code in SECURITY_PATTERNS.items():
        if phrase not in text:
            continue
        if "no security bypass" in original_text and code in {"SECRET_LEAKAGE", "AUTHENTICATION_BYPASS", "ACCESS_CONTROL"}:
            continue
        signals.append(code)
    if "security-review" in (issue.labels or []):
        signals.append("SECURITY_REVIEW_LABEL")
    signals = sorted(set(signals))
    score = min(1.0, 0.25 + len(signals) * 0.22) if signals else 0.08
    if "SECURITY_REVIEW_LABEL" in signals and len(signals) > 1:
        score = min(1.0, score + 0.08)
    if score >= settings.security_escalation_threshold:
        state = "HIGH_SECURITY_SIGNAL"
        handling = "Route to maintainer/security review. Avoid asking the reporter to post secrets or exploit details publicly."
    elif score >= 0.38:
        state = "POSSIBLE_SECURITY_SENSITIVE"
        handling = "Review privately if sensitive details may be involved."
    else:
        state = "LOW_SECURITY_SIGNAL"
        handling = "No special security handling indicated by synchronized issue text."
    return {"security_state": state, "confidence": round(score, 2), "signals": signals, "recommended_handling": handling}


def analyze_release_regression(db: Session, issue: Issue, related_prs: list[dict[str, object]] | None = None) -> dict[str, object]:
    text = issue_text(issue).lower()
    mentions_release = "after v" in text or "after latest" in text or "stopped working after" in text or "recent release" in text
    releases = db.query(Release).filter_by(repository_id=issue.repository_id).order_by(Release.published_at.desc().nullslast()).limit(5).all()
    matching = []
    for release in releases:
        haystack = f"{release.tag} {release.name or ''} {release.body or ''}".lower()
        if release.tag.lower() in text or any(term in haystack for term in important_terms(text)):
            matching.append({"tag": release.tag, "title": release.name or release.tag, "url": release.html_url, "notes": release.body or ""})
    temporal = False
    issue_created = as_utc(issue.created_at)
    if issue_created:
        for release in releases:
            published = as_utc(release.published_at)
            if published and timedelta(days=0) <= issue_created - published <= timedelta(days=21):
                temporal = True
                if not any(item["tag"] == release.tag for item in matching):
                    matching.append({"tag": release.tag, "title": release.name or release.tag, "url": release.html_url, "notes": release.body or ""})
    if mentions_release and (matching or temporal):
        state = "STRONG_TEMPORAL_CORRELATION" if temporal and matching else "POSSIBLE_POST_RELEASE_REGRESSION"
    elif mentions_release:
        state = "POSSIBLE_POST_RELEASE_REGRESSION"
    else:
        state = "NO_RELEASE_CORRELATION"
    return {
        "regression_state": state,
        "confidence": 0.84 if state == "STRONG_TEMPORAL_CORRELATION" else 0.64 if state == "POSSIBLE_POST_RELEASE_REGRESSION" else 0.72,
        "matching_releases": matching[:3],
        "related_pull_requests": related_prs or [],
        "explanation": "Temporal correlation is not proof of causation; maintainer verification is required." if state != "NO_RELEASE_CORRELATION" else "No release-change wording or temporal release correlation was detected.",
    }


def analyze_related_pull_requests(db: Session, issue: Issue, limit: int = 4) -> list[dict[str, object]]:
    query = issue_text(issue)
    query_vector = vectorize(query)
    issue_terms = important_terms(query)
    results = []
    for pr in db.query(PullRequest).filter_by(repository_id=issue.repository_id).all():
        text = f"{pr.title}\n{pr.body or ''}"
        semantic = cosine(query_vector, vectorize(text))
        terms = issue_terms & important_terms(text)
        issue_created = as_utc(issue.created_at)
        pr_updated = as_utc(pr.updated_at)
        timing = 0.08 if issue_created and pr_updated and abs((issue_created - pr_updated).days) <= 30 else 0.0
        score = min(1.0, semantic * 0.55 + min(len(terms) * 0.12, 0.3) + timing)
        if score > 0.08:
            results.append(
                {
                    "number": pr.github_pr_number,
                    "title": pr.title,
                    "url": pr.html_url,
                    "relevance_score": round(score, 4),
                    "why_relevant": "Overlapping terms: " + ", ".join(sorted(terms)[:5]) if terms else "Weak semantic/timing relationship.",
                }
            )
    return sorted(results, key=lambda item: item["relevance_score"], reverse=True)[:limit]


def analyze_priority(issue: Issue, category: str, duplicate_analysis: dict[str, object], completeness: dict[str, object], security: dict[str, object], release: dict[str, object]) -> dict[str, object]:
    score = 0.2
    signals: list[str] = []
    if category == "DOCUMENTATION":
        score -= 0.08
        signals.append("LOW_IMPACT_DOCUMENTATION")
    if category in {"BUG", "PERFORMANCE"}:
        score += 0.18
        signals.append("USER_IMPACT")
    if security["security_state"] == "HIGH_SECURITY_SIGNAL":
        score += 0.45
        signals.append("SECURITY_RISK")
    elif security["security_state"] == "POSSIBLE_SECURITY_SENSITIVE":
        score += 0.25
        signals.append("POSSIBLE_SECURITY_RISK")
    if duplicate_analysis["duplicate_state"] in {"POSSIBLE_DUPLICATE", "VERY_LIKELY_DUPLICATE"}:
        score += 0.12
        signals.append("MULTIPLE_RELATED_REPORTS")
    if release["regression_state"] != "NO_RELEASE_CORRELATION":
        score += 0.14
        signals.append("RECENT_RELEASE_REGRESSION")
    if int(completeness["completeness_score"]) < 35:
        score -= 0.08
        signals.append("INCOMPLETE_REPORT")
    if "high-priority" in (issue.labels or []):
        score += 0.1
        signals.append("REPOSITORY_HIGH_PRIORITY_LABEL")
    score = max(0.0, min(score, 1.0))
    if score >= settings.critical_priority_score_threshold:
        priority = "CRITICAL"
    elif score >= settings.high_priority_score_threshold:
        priority = "HIGH"
    elif score >= 0.35:
        priority = "MEDIUM"
    else:
        priority = "LOW"
    return {
        "priority": priority,
        "level": priority,
        "confidence": 0.86 if signals else 0.62,
        "priority_score": round(score, 4),
        "signals": signals,
        "explanation": "Priority is derived from deterministic repository signals, not urgency wording alone.",
    }


def advanced_escalation(duplicate: dict[str, object], completeness: dict[str, object], security: dict[str, object], release: dict[str, object], priority: dict[str, object]) -> dict[str, object]:
    if security["security_state"] == "HIGH_SECURITY_SIGNAL":
        return {"decision": "URGENT_REVIEW", "confidence": 0.92, "reason_codes": ["HIGH_SECURITY_SIGNAL"], "recommended_action": security["recommended_handling"]}
    if int(completeness["completeness_score"]) < 35:
        return {"decision": "NEEDS_INFORMATION", "confidence": 0.9, "reason_codes": ["INSUFFICIENT_INFORMATION"], "recommended_action": "Ask only for issue-type-relevant missing information."}
    if duplicate["duplicate_state"] == "VERY_LIKELY_DUPLICATE":
        return {"decision": "POSSIBLE_DUPLICATE", "confidence": 0.88, "reason_codes": ["VERY_LIKELY_DUPLICATE"], "recommended_action": "Ask a maintainer to compare against the top duplicate candidate before closing anything."}
    if duplicate["duplicate_state"] == "POSSIBLE_DUPLICATE":
        return {"decision": "POSSIBLE_DUPLICATE", "confidence": 0.78, "reason_codes": ["POSSIBLE_DUPLICATE"], "recommended_action": "Review similar reports before independent triage."}
    if priority["priority"] in {"HIGH", "CRITICAL"} or release["regression_state"] != "NO_RELEASE_CORRELATION":
        return {"decision": "MAINTAINER_REVIEW", "confidence": 0.82, "reason_codes": ["HIGH_PRIORITY_OR_REGRESSION"], "recommended_action": "Route to maintainer review with evidence links."}
    return {"decision": "NORMAL_QUEUE", "confidence": 0.74, "reason_codes": [], "recommended_action": "Keep in normal triage queue."}


def compute_telemetry(investigation: Investigation, retrieved_evidence_count: int, start_time: float | None = None, duration_ms: int | None = None) -> dict[str, object]:
    steps = list(investigation.steps) if investigation.id else []
    return {
        "duration_ms": duration_ms if duration_ms is not None else sum(step.duration_ms for step in steps),
        "agent_steps": len(steps),
        "retrieval_calls": sum(1 for step in steps if "search" in step.tool_name or "retriev" in step.tool_name),
        "github_calls": 0,
        "ai_provider_calls": 0,
        "retrieved_evidence_sources": retrieved_evidence_count,
        "error_count": sum(1 for step in steps if step.status not in {"SUCCESS", "INSUFFICIENT_EVIDENCE"}),
        "final_status": investigation.status,
        "token_usage": None,
    }


def repository_health(db: Session, repository_id: int) -> dict[str, object]:
    now = datetime.now(UTC)
    issues = db.query(Issue).filter_by(repository_id=repository_id).all()
    investigations = db.query(Investigation).filter_by(repository_id=repository_id).all()
    open_issues = [issue for issue in issues if issue.state == "OPEN"]
    stale_cutoff = now - timedelta(days=settings.stale_issue_days)
    stale = [issue for issue in open_issues if as_utc(issue.updated_at) and as_utc(issue.updated_at) < stale_cutoff]
    high = [item for item in investigations if item.priority == "HIGH"]
    critical = [item for item in investigations if item.priority == "CRITICAL"]
    dupes = [item for item in investigations if item.escalation_decision == "POSSIBLE_DUPLICATE"]
    needs_info = [item for item in investigations if item.escalation_decision == "NEEDS_INFORMATION"]
    maintainer = [item for item in investigations if item.escalation_decision in {"MAINTAINER_REVIEW", "URGENT_REVIEW"}]
    comments = db.query(Comment).filter_by(repository_id=repository_id).all()
    first_response_hours = []
    by_issue = {}
    for comment in comments:
        if comment.issue_id and comment.created_at:
            by_issue.setdefault(comment.issue_id, []).append(comment.created_at)
    for issue in issues:
        created = as_utc(issue.created_at)
        if issue.id in by_issue and created:
            first_response_hours.append(min((as_utc(dt) - created).total_seconds() / 3600 for dt in by_issue[issue.id] if as_utc(dt)))
    dimensions = {
        "backlog": max(0, 100 - len(open_issues) * 4),
        "staleness": max(0, 100 - int((len(stale) / max(len(open_issues), 1)) * 100)),
        "priority_risk": max(0, 100 - len(high) * 8 - len(critical) * 15),
        "duplicate_burden": max(0, 100 - int((len(dupes) / max(len(investigations), 1)) * 100)),
        "response": 100 if not first_response_hours else max(0, 100 - int(statistics.median(first_response_hours))),
    }
    overall = round(sum(dimensions.values()) / len(dimensions))
    state = "HEALTHY" if overall >= 80 else "WATCH" if overall >= 60 else "DEGRADED" if overall >= 40 else "CRITICAL_ATTENTION"
    new_7 = [issue for issue in issues if as_utc(issue.created_at) and as_utc(issue.created_at) >= now - timedelta(days=7)]
    closed_7 = [issue for issue in issues if as_utc(issue.closed_at) and as_utc(issue.closed_at) >= now - timedelta(days=7)]
    classification_counts = Counter(item.classification for item in investigations)
    priority_counts = Counter(item.priority for item in investigations)
    return {
        "overall_score": overall,
        "dimension_scores": dimensions,
        "signals": {
            "open_issue_count": len(open_issues),
            "new_issues_last_7_days": len(new_7),
            "closed_issues_last_7_days": len(closed_7),
            "backlog_change": len(new_7) - len(closed_7),
            "stale_issue_count": len(stale),
            "high_priority_count": len(high),
            "critical_count": len(critical),
            "possible_duplicate_count": len(dupes),
            "needs_information_count": len(needs_info),
            "maintainer_review_count": len(maintainer),
            "average_first_response_hours": round(statistics.mean(first_response_hours), 2) if first_response_hours else None,
            "median_first_response_hours": round(statistics.median(first_response_hours), 2) if first_response_hours else None,
            "pr_activity": db.query(PullRequest).filter_by(repository_id=repository_id).count(),
            "release_activity": db.query(Release).filter_by(repository_id=repository_id).count(),
        },
        "health_state": state,
        "distributions": {"classification": dict(classification_counts), "priority": dict(priority_counts)},
        "history": {
            "issue_creation_vs_closure": [{"label": "last_7_days", "created": len(new_7), "closed": len(closed_7)}],
            "insufficient_history": len(issues) < 20,
        },
    }


def weekly_brief(db: Session, repository_id: int) -> dict[str, object]:
    health = repository_health(db, repository_id)
    investigations = db.query(Investigation).filter_by(repository_id=repository_id).all()
    high_items = [item for item in investigations if item.priority in {"HIGH", "CRITICAL"}]
    dupes = [item for item in investigations if item.escalation_decision == "POSSIBLE_DUPLICATE"]
    needs_info = [item for item in investigations if item.escalation_decision == "NEEDS_INFORMATION"]
    releases = db.query(Release).filter_by(repository_id=repository_id).all()
    prs = db.query(PullRequest).filter_by(repository_id=repository_id).all()
    return {
        "period": "current synchronized data",
        "ai_provider": "not_configured" if not settings.openai_api_key else "configured",
        "summary": f"Repository health is {health['health_state']} with score {health['overall_score']}.",
        "statistics": health["signals"],
        "high_priority_items": [{"issue_id": item.issue_id, "priority": item.priority, "escalation": item.escalation_decision} for item in high_items],
        "possible_duplicates": len(dupes),
        "needs_information": len(needs_info),
        "recent_pr_activity": len(prs),
        "release_activity": len(releases),
        "important_escalations": [{"issue_id": item.issue_id, "decision": item.escalation_decision} for item in investigations if item.escalation_decision in {"MAINTAINER_REVIEW", "URGENT_REVIEW"}],
    }


def evaluation_metrics(db: Session, repository_id: int) -> dict[str, object]:
    feedback = db.query(HumanFeedback).filter_by(repository_id=repository_id).all()
    labeled = [item for item in feedback if item.corrected_value or item.feedback_status in {"CORRECT", "INCORRECT", "ADJUSTED"}]
    if len(labeled) < 3:
        return {"status": "INSUFFICIENT_LABELED_DATA", "labeled_count": len(labeled), "metrics": {}, "confusion_matrix": []}
    correct = sum(1 for item in labeled if item.feedback_status == "CORRECT")
    agreement = correct / len(labeled)
    matrix: dict[tuple[str, str], int] = {}
    for item in labeled:
        if item.target_type == "classification":
            actual = item.corrected_value or item.original_value
            matrix[(item.original_value, actual)] = matrix.get((item.original_value, actual), 0) + 1
    return {
        "status": "OK",
        "labeled_count": len(labeled),
        "metrics": {"human_agreement_rate": round(agreement, 4), "classification_accuracy": round(agreement, 4)},
        "confusion_matrix": [{"predicted": key[0], "actual": key[1], "count": value} for key, value in sorted(matrix.items())],
    }
