from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ActionRecommendation, IndexedDocument, Investigation, Issue, PullRequest, Release, Repository
from app.rag.retriever import search_repository_history
from app.services.advanced_intelligence import analyze_completeness, analyze_duplicates, analyze_related_pull_requests, analyze_release_regression, analyze_security, repository_health, weekly_brief
from app.services.github_sync import connect_repository, sync_repository

RHD_INTENTS = {
    "FULL_REPOSITORY_REVIEW",
    "HEALTH_EXPLANATION",
    "TOP_PRIORITIES",
    "ISSUE_LOOKUP",
    "DUPLICATE_ANALYSIS",
    "SECURITY_REVIEW",
    "RELEASE_ANALYSIS",
    "PR_ANALYSIS",
    "NEEDS_INFORMATION",
    "REPOSITORY_SEARCH",
    "MAINTAINER_BRIEF",
    "ACTION_RECOMMENDATION",
    "UNKNOWN",
}

CLUSTER_TERMS = {
    "Authentication": ["auth", "login", "password", "credential", "session"],
    "Uploads": ["upload", "image", "file", "png", "jpeg"],
    "Documentation": ["readme", "docs", "documentation", "install", "typo"],
    "Performance": ["slow", "performance", "freeze", "latency", "timeout"],
    "Security": ["security", "secret", "api key", "credential", "vulnerability"],
    "Features": ["feature", "request", "support", "enhancement"],
    "Maintenance": ["dependency", "refactor", "cleanup", "ci", "test"],
}


@dataclass(frozen=True)
class ParsedRepository:
    full_name: str
    html_url: str


def parse_repository_input(value: str) -> ParsedRepository:
    text = value.strip()
    github_url = re.match(r"^(?:https://)?github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?(?:[?#].*)?$", text, re.IGNORECASE)
    owner_repo = re.match(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$", text)
    match = github_url or owner_repo
    if not match:
        raise ValueError("Enter a GitHub repository as owner/repository or https://github.com/owner/repository")
    owner, repo = match.group(1), match.group(2)
    full_name = f"{owner}/{repo.removesuffix('.git')}"
    return ParsedRepository(full_name=full_name, html_url=f"https://github.com/{full_name}")


def repository_access_mode(repo: Repository) -> str:
    return "WRITE_ENABLED_DEMO" if repo.full_name == settings.allowed_write_repository else "READ_ONLY_PUBLIC"


def route_intent(question: str) -> str:
    text = question.lower().strip()
    if not text:
        return "FULL_REPOSITORY_REVIEW"
    if any(term in text for term in ["invent", "fabricate", "ignore repository evidence", "ignore evidence"]):
        return "UNKNOWN"
    if any(term in text for term in ["full review", "review repo", "repository review", "executive assessment"]):
        return "FULL_REPOSITORY_REVIEW"
    if any(term in text for term in ["health", "degraded", "watch", "score"]):
        return "HEALTH_EXPLANATION"
    if any(term in text for term in ["fix first", "priority", "priorities", "today", "risks", "critical"]):
        return "TOP_PRIORITIES"
    if any(term in text for term in ["duplicate", "similar", "cluster"]):
        return "DUPLICATE_ANALYSIS"
    if any(term in text for term in ["security", "secret", "credential", "vulnerability"]):
        return "SECURITY_REVIEW"
    if any(term in text for term in ["release", "regression", "v1.", "after"]):
        return "RELEASE_ANALYSIS"
    if any(term in text for term in ["pull request", " pr ", "prs"]):
        return "PR_ANALYSIS"
    if any(term in text for term in ["needs info", "missing information", "incomplete", "more information"]):
        return "NEEDS_INFORMATION"
    if any(term in text for term in ["queue", "approval", "recommendation", "action"]):
        return "ACTION_RECOMMENDATION"
    issue_match = re.search(r"#(\d+)|issue\s+(\d+)", text)
    if issue_match:
        return "ISSUE_LOOKUP"
    if any(term in text for term in ["brief", "manager", "maintainer"]):
        return "MAINTAINER_BRIEF"
    if len(text.split()) >= 2:
        return "REPOSITORY_SEARCH"
    return "UNKNOWN"


def onboard_repository(db: Session, repository_input: str, run_sync: bool = True) -> dict[str, Any]:
    parsed = parse_repository_input(repository_input)
    repo, created = connect_repository(db, parsed.full_name)
    sync_result: dict[str, Any] | None = None
    if run_sync:
        sync_result = sync_repository(db, repo.id)
    return {
        "status": "connected",
        "created": created,
        "repository": repo_summary(db, repo),
        "access_mode": repository_access_mode(repo),
        "sync_result": sync_result,
        "rhd_status": "READY" if not run_sync else "INDEXING_COMPLETE",
        "initial_scan": initial_scan(db, repo.id),
        "review": full_repository_review(db, repo.id),
    }


def repo_summary(db: Session, repo: Repository) -> dict[str, Any]:
    return {
        "id": repo.id,
        "full_name": repo.full_name,
        "html_url": repo.html_url,
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "last_synced_at": repo.last_synced_at,
        "access_mode": repository_access_mode(repo),
        "indexed_documents": db.query(IndexedDocument).filter_by(repository_id=repo.id).count(),
    }


def latest_investigations(db: Session, repository_id: int) -> dict[int, Investigation]:
    latest: dict[int, Investigation] = {}
    for item in db.query(Investigation).filter_by(repository_id=repository_id).order_by(Investigation.created_at).all():
        latest[item.issue_id] = item
    return latest


def repository_snapshot(db: Session, repository_id: int) -> dict[str, Any]:
    repo = db.get(Repository, repository_id)
    if not repo:
        raise ValueError("Repository not found")
    issues = db.query(Issue).filter_by(repository_id=repository_id).order_by(Issue.github_issue_number).all()
    prs = db.query(PullRequest).filter_by(repository_id=repository_id).order_by(PullRequest.github_pr_number).all()
    releases = db.query(Release).filter_by(repository_id=repository_id).order_by(Release.published_at.desc().nullslast()).all()
    recommendations = db.query(ActionRecommendation).filter_by(repository_id=repository_id).all()
    latest = latest_investigations(db, repository_id)
    return {
        "repository": repo,
        "issues": issues,
        "pull_requests": prs,
        "releases": releases,
        "recommendations": recommendations,
        "latest_investigations": latest,
        "health": repository_health(db, repository_id),
        "brief": weekly_brief(db, repository_id),
        "indexed_documents": db.query(IndexedDocument).filter_by(repository_id=repository_id).count(),
    }


def initial_scan(db: Session, repository_id: int) -> dict[str, Any]:
    snap = repository_snapshot(db, repository_id)
    issues = snap["issues"]
    latest = snap["latest_investigations"]
    duplicate_count = sum(1 for item in latest.values() if item.escalation_decision == "POSSIBLE_DUPLICATE")
    needs_info_count = sum(1 for item in latest.values() if item.escalation_decision == "NEEDS_INFORMATION")
    security_count = sum(1 for issue in issues if analyze_security(issue)["security_state"] != "LOW_SECURITY_SIGNAL")
    release_count = sum(1 for issue in issues if analyze_release_regression(db, issue)["regression_state"] != "NO_RELEASE_CORRELATION")
    steps = [
        ("Repository metadata", "COMPLETED", snap["repository"].full_name),
        ("Issue backlog", "COMPLETED", f"{len(issues)} synchronized issues"),
        ("Pull request activity", "COMPLETED", f"{len(snap['pull_requests'])} synchronized pull requests"),
        ("Release history", "COMPLETED", f"{len(snap['releases'])} synchronized releases"),
        ("Issue categories", "COMPLETED", f"{len(latest)} analyzed issues"),
        ("Duplicate clusters", "COMPLETED", f"{duplicate_count} duplicate escalation signals"),
        ("Missing-information burden", "COMPLETED", f"{needs_info_count} needs-information signals"),
        ("Security-sensitive signals", "COMPLETED", f"{security_count} security-sensitive issue signals"),
        ("Priority distribution", "COMPLETED", dict(Counter(item.priority for item in latest.values()))),
        ("Possible release regressions", "COMPLETED", f"{release_count} release-correlation signals"),
        ("Pending maintainer actions", "COMPLETED", f"{len([item for item in snap['recommendations'] if item.status == 'PENDING'])} pending recommendations"),
        ("Available repository evidence", "COMPLETED", f"{snap['indexed_documents']} indexed documents"),
        ("Overall health assessment", "COMPLETED", f"{snap['health']['health_state']} {snap['health']['overall_score']}/100"),
        ("Recommended next actions", "COMPLETED", f"{len(top_actions(db, repository_id, 5))} generated actions"),
    ]
    return {"status": "COMPLETED", "steps": [{"name": name, "status": status, "summary": summary} for name, status, summary in steps]}


def executive_assessment(db: Session, repository_id: int) -> dict[str, Any]:
    snap = repository_snapshot(db, repository_id)
    latest = snap["latest_investigations"]
    health = snap["health"]
    signals = health["signals"]
    risks: list[str] = []
    if signals.get("high_priority_count", 0):
        risks.append(f"{signals['high_priority_count']} high-priority investigation signals")
    if signals.get("possible_duplicate_count", 0):
        risks.append(f"{signals['possible_duplicate_count']} possible duplicate investigation signals")
    if signals.get("needs_information_count", 0):
        risks.append(f"{signals['needs_information_count']} issues need more information")
    security = [issue for issue in snap["issues"] if analyze_security(issue)["security_state"] != "LOW_SECURITY_SIGNAL"]
    if security:
        risks.append(f"{len(security)} security-sensitive issue signals")
    focus = "Review pending human actions and high-priority issues." if latest else "Run investigations to enrich repository intelligence."
    return {
        "state": health["health_state"],
        "health_score": health["overall_score"],
        "main_signals": risks or ["No high-risk synchronized signals found."],
        "top_risks": risks[:5],
        "recommended_maintainer_focus": focus,
    }


def top_actions(db: Session, repository_id: int, limit: int = 5) -> list[dict[str, Any]]:
    snap = repository_snapshot(db, repository_id)
    actions: list[dict[str, Any]] = []
    latest = snap["latest_investigations"]
    pending_by_issue = {item.issue_id: item for item in snap["recommendations"] if item.status == "PENDING"}
    for issue in snap["issues"]:
        investigation = latest.get(issue.id)
        security = analyze_security(issue)
        release = analyze_release_regression(db, issue)
        rank = 0
        reasons: list[str] = []
        if security["security_state"] == "HIGH_SECURITY_SIGNAL":
            rank += 90
            reasons.append("security-sensitive signal")
        if investigation and investigation.priority == "CRITICAL":
            rank += 80
            reasons.append("critical priority")
        if investigation and investigation.priority == "HIGH":
            rank += 65
            reasons.append("high priority")
        if investigation and investigation.escalation_decision == "NEEDS_INFORMATION":
            rank += 48
            reasons.append("missing information")
        if investigation and investigation.escalation_decision == "POSSIBLE_DUPLICATE":
            rank += 45
            reasons.append("possible duplicate")
        if release["regression_state"] != "NO_RELEASE_CORRELATION":
            rank += 38
            reasons.append("possible release regression")
        if issue.id in pending_by_issue:
            rank += 30
            reasons.append("pending human action")
        if not reasons:
            continue
        actions.append(
            {
                "priority": "HIGH" if rank >= 65 else "MEDIUM",
                "rank": rank,
                "reason": ", ".join(reasons),
                "evidence": [{"type": "Issue", "label": f"#{issue.github_issue_number}", "title": issue.title, "url": issue.html_url}],
                "affected": {"type": "issue", "number": issue.github_issue_number, "id": issue.id, "title": issue.title, "url": issue.html_url},
                "recommended_human_action": _recommended_human_action(issue, investigation, security, release, pending_by_issue.get(issue.id)),
            }
        )
    return sorted(actions, key=lambda item: item["rank"], reverse=True)[:limit]


def _recommended_human_action(issue: Issue, investigation: Investigation | None, security: dict[str, Any], release: dict[str, Any], recommendation: ActionRecommendation | None) -> str:
    if recommendation:
        return f"Open Review Queue and inspect the {recommendation.action_type} recommendation."
    if security["security_state"] == "HIGH_SECURITY_SIGNAL":
        return "Review privately before asking for more details; do not request secrets publicly."
    if investigation and investigation.escalation_decision == "NEEDS_INFORMATION":
        return "Request the missing reproduction or environment details."
    if investigation and investigation.escalation_decision == "POSSIBLE_DUPLICATE":
        return "Compare related issues and consolidate only after maintainer confirmation."
    if release["regression_state"] != "NO_RELEASE_CORRELATION":
        return "Compare the issue timeline against recent release notes and related PRs."
    return f"Open Issue #{issue.github_issue_number} and continue triage."


def issue_clusters(db: Session, repository_id: int) -> list[dict[str, Any]]:
    issues = db.query(Issue).filter_by(repository_id=repository_id).all()
    latest = latest_investigations(db, repository_id)
    buckets: dict[str, list[Issue]] = defaultdict(list)
    for issue in issues:
        text = f"{issue.title} {issue.body or ''} {' '.join(issue.labels or [])}".lower()
        matched = False
        for name, terms in CLUSTER_TERMS.items():
            if any(term in text for term in terms):
                buckets[name].append(issue)
                matched = True
                break
        if not matched and issue.id in latest:
            buckets[latest[issue.id].classification.title().replace("_", " ")].append(issue)
    clusters = []
    for name, items in sorted(buckets.items()):
        priorities = Counter(latest[item.id].priority for item in items if item.id in latest)
        duplicate_count = sum(1 for item in items if item.id in latest and latest[item.id].escalation_decision == "POSSIBLE_DUPLICATE")
        risk = "HIGH" if priorities.get("CRITICAL") or priorities.get("HIGH", 0) >= 2 else "MEDIUM" if priorities.get("HIGH") or duplicate_count else "LOW"
        clusters.append(
            {
                "name": name,
                "issue_count": len(items),
                "risk": risk,
                "priority_distribution": dict(priorities),
                "duplicate_concentration": duplicate_count,
                "representative_issues": [{"number": item.github_issue_number, "title": item.title, "url": item.html_url} for item in items[:4]],
            }
        )
    return clusters


def duplicate_clusters(db: Session, repository_id: int) -> list[dict[str, Any]]:
    issues = db.query(Issue).filter_by(repository_id=repository_id).order_by(Issue.github_issue_number).limit(30).all()
    seen: set[int] = set()
    clusters = []
    for issue in issues:
        if issue.id in seen:
            continue
        duplicate = analyze_duplicates(db, issue, limit=5)
        candidates = [item for item in duplicate["duplicate_candidates"] if float(item["final_duplicate_score"]) >= settings.duplicate_possible_threshold]
        if not candidates:
            continue
        seen.add(issue.id)
        member_numbers = [issue.github_issue_number]
        members = [{"number": issue.github_issue_number, "title": issue.title, "url": issue.html_url}]
        for candidate in candidates:
            seen.add(int(candidate["candidate_issue_id"]))
            member_numbers.append(int(candidate["github_issue_number"]))
            members.append({"number": candidate["github_issue_number"], "title": candidate["title"], "url": candidate["url"], "score": candidate["final_duplicate_score"]})
        clusters.append(
            {
                "name": f"Issue #{min(member_numbers)} duplicate cluster",
                "similarity": "HIGH" if float(duplicate["top_score"]) >= settings.duplicate_very_likely_threshold else "MEDIUM",
                "top_score": duplicate["top_score"],
                "members": members,
                "recommended": "Maintainer review for consolidation. RHD will not close issues automatically.",
            }
        )
    return clusters[:6]


def maintainer_workload(db: Session, repository_id: int) -> dict[str, Any]:
    snap = repository_snapshot(db, repository_id)
    latest = snap["latest_investigations"]
    pending = [item for item in snap["recommendations"] if item.status == "PENDING"]
    high = [item for item in latest.values() if item.priority in {"HIGH", "CRITICAL"}]
    security = [issue for issue in snap["issues"] if analyze_security(issue)["security_state"] != "LOW_SECURITY_SIGNAL"]
    needs_info = [item for item in latest.values() if item.escalation_decision == "NEEDS_INFORMATION"]
    open_prs = [item for item in snap["pull_requests"] if item.state == "OPEN"]
    score = len(pending) * 2 + len(high) * 3 + len(security) * 3 + len(needs_info) + len(open_prs)
    load = "OVERLOADED" if score >= 30 else "HIGH" if score >= 18 else "MODERATE" if score >= 8 else "LOW"
    return {
        "load": load,
        "score": score,
        "rules": "pending*2 + high_priority*3 + security*3 + needs_information + open_prs",
        "signals": {
            "pending_human_actions": len(pending),
            "high_priority_issues": len(high),
            "security_review_queue": len(security),
            "needs_information_issues": len(needs_info),
            "open_pull_requests": len(open_prs),
        },
    }


def full_repository_review(db: Session, repository_id: int) -> dict[str, Any]:
    snap = repository_snapshot(db, repository_id)
    repo = snap["repository"]
    assessment = executive_assessment(db, repository_id)
    clusters = issue_clusters(db, repository_id)
    duplicate = duplicate_clusters(db, repository_id)
    actions = top_actions(db, repository_id, 5)
    security = [
        {"number": issue.github_issue_number, "title": issue.title, "url": issue.html_url, "signal": analyze_security(issue)}
        for issue in snap["issues"]
        if analyze_security(issue)["security_state"] != "LOW_SECURITY_SIGNAL"
    ]
    incomplete = []
    latest = snap["latest_investigations"]
    for issue in snap["issues"]:
        category = latest[issue.id].classification if issue.id in latest else "BUG"
        completeness = analyze_completeness(issue, category)
        if int(completeness["score"]) < 60:
            incomplete.append({"number": issue.github_issue_number, "title": issue.title, "url": issue.html_url, "score": completeness["score"], "missing": completeness["missing_information"]})
    return {
        "repository": repo_summary(db, repo),
        "generated_at": datetime.now(UTC).isoformat(),
        "executive_assessment": assessment,
        "health": snap["health"],
        "issue_backlog": {"total": len(snap["issues"]), "open": len([item for item in snap["issues"] if item.state == "OPEN"]), "clusters": clusters},
        "pr_activity": {"total": len(snap["pull_requests"]), "open": len([item for item in snap["pull_requests"] if item.state == "OPEN"])},
        "release_stability": {"releases": len(snap["releases"]), "release_related_issues": [item for item in top_actions(db, repository_id, 10) if "release" in item["reason"]]},
        "duplicate_burden": {"clusters": duplicate, "count": len(duplicate)},
        "incomplete_reports": incomplete[:8],
        "security_signals": security[:8],
        "high_priority_issues": [
            {"number": issue.github_issue_number, "title": issue.title, "url": issue.html_url, "priority": latest[issue.id].priority}
            for issue in snap["issues"]
            if issue.id in latest and latest[issue.id].priority in {"HIGH", "CRITICAL"}
        ],
        "maintainer_workload": maintainer_workload(db, repository_id),
        "top_risks": assessment["top_risks"],
        "top_opportunities": ["Consolidate duplicate reports", "Request missing information early", "Keep security-sensitive reports in human review"],
        "recommended_action_plan": actions,
        "evidence": _review_evidence(db, repository_id),
        "automation_level": {
            "analyze": "AUTOMATIC",
            "recommend": "AUTOMATIC",
            "external_action": "HUMAN_APPROVAL_REQUIRED",
        },
        "confidence": confidence_for_review(snap),
    }


def _review_evidence(db: Session, repository_id: int) -> list[dict[str, Any]]:
    return [
        {"source_type": item.source_type, "github_number": item.github_number, "title": item.title, "source_url": item.source_url}
        for item in db.query(IndexedDocument).filter_by(repository_id=repository_id).order_by(IndexedDocument.indexed_at.desc()).limit(12).all()
    ]


def confidence_for_review(snap: dict[str, Any]) -> str:
    if snap["indexed_documents"] >= 10 and snap["latest_investigations"]:
        return "High"
    if snap["indexed_documents"]:
        return "Medium"
    return "Low"


def answer_question(db: Session, repository_id: int, question: str, session_context: dict[str, Any] | None = None) -> dict[str, Any]:
    intent = route_intent(question)
    trace = [{"step": "Classified controlled RHD intent", "status": "COMPLETED", "summary": intent}]
    if intent == "UNKNOWN":
        return refusal_response(question, trace)
    repo = db.get(Repository, repository_id)
    if not repo:
        raise ValueError("Repository not found")
    trace.append({"step": "Loaded repository context", "status": "COMPLETED", "summary": repo.full_name})
    review = full_repository_review(db, repository_id)
    trace.append({"step": "Loaded health, issues, PRs, releases, review queue, and evidence", "status": "COMPLETED", "summary": "Repository-scoped tools completed"})
    answer = _intent_answer(db, repository_id, intent, question, review)
    trace.append({"step": "Generated structured RHD assessment", "status": "COMPLETED", "summary": "No private reasoning exposed"})
    return {
        "question": question,
        "intent": intent,
        "answer": answer["answer"],
        "key_findings": answer["key_findings"],
        "evidence": answer["evidence"],
        "recommended_actions": answer["recommended_actions"],
        "confidence": answer["confidence"],
        "sources": answer["sources"],
        "trace": trace,
        "context": {"repository_id": repository_id, "last_intent": intent, "last_issue": answer.get("last_issue")},
    }


def refusal_response(question: str, trace: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "question": question,
        "intent": "UNKNOWN",
        "answer": "RHD cannot fabricate repository evidence or ignore synchronized repository data. Ask for a review, priorities, duplicates, security signals, release risk, or repository search.",
        "key_findings": ["Insufficient repository evidence for the requested unsupported claim."],
        "evidence": [],
        "recommended_actions": ["Ask an evidence-grounded repository question."],
        "confidence": "High",
        "sources": [],
        "trace": trace + [{"step": "Applied evidence-grounding guardrail", "status": "COMPLETED", "summary": "Refused unsupported request"}],
        "context": {},
    }


def _intent_answer(db: Session, repository_id: int, intent: str, question: str, review: dict[str, Any]) -> dict[str, Any]:
    sources = review["evidence"][:6]
    if intent == "FULL_REPOSITORY_REVIEW":
        return {
            "answer": f"{review['executive_assessment']['state']} - {review['executive_assessment']['health_score']}/100. RHD reviewed synchronized issues, PRs, releases, indexed evidence, and pending maintainer actions.",
            "key_findings": review["executive_assessment"]["main_signals"],
            "evidence": sources,
            "recommended_actions": [item["recommended_human_action"] for item in review["recommended_action_plan"]],
            "confidence": review["confidence"],
            "sources": sources,
        }
    if intent == "HEALTH_EXPLANATION":
        health = review["health"]
        return {
            "answer": f"Repository health is {health['health_state']} at {health['overall_score']}/100.",
            "key_findings": [f"{key}: {value}" for key, value in health["dimension_scores"].items()],
            "evidence": [{"source_type": "repository analytics", "title": "Repository Health", "source_url": None}],
            "recommended_actions": [review["executive_assessment"]["recommended_maintainer_focus"]],
            "confidence": review["confidence"],
            "sources": [{"source_type": "repository analytics", "title": "Repository Health", "source_url": None}],
        }
    if intent == "TOP_PRIORITIES":
        actions = review["recommended_action_plan"]
        return {
            "answer": "RHD ranked today's maintainer priorities from security, priority, escalation, release, duplicate, and pending-action signals.",
            "key_findings": [f"{item['affected']['number']}: {item['reason']}" for item in actions],
            "evidence": [evidence for item in actions for evidence in item["evidence"]][:8],
            "recommended_actions": [item["recommended_human_action"] for item in actions],
            "confidence": review["confidence"],
            "sources": [evidence for item in actions for evidence in item["evidence"]][:8],
        }
    if intent == "DUPLICATE_ANALYSIS":
        clusters = review["duplicate_burden"]["clusters"]
        return {
            "answer": f"RHD found {len(clusters)} duplicate clusters from repository duplicate scoring.",
            "key_findings": [f"{cluster['name']} score {cluster['top_score']}" for cluster in clusters] or ["No duplicate clusters above threshold."],
            "evidence": [member for cluster in clusters for member in cluster["members"]][:8],
            "recommended_actions": [cluster["recommended"] for cluster in clusters[:5]],
            "confidence": "Medium" if clusters else "High",
            "sources": [member for cluster in clusters for member in cluster["members"]][:8],
        }
    if intent == "SECURITY_REVIEW":
        signals = review["security_signals"]
        return {
            "answer": f"RHD found {len(signals)} security-sensitive issue signals. This is not vulnerability confirmation.",
            "key_findings": [f"Issue #{item['number']}: {item['signal']['security_state']}" for item in signals] or ["No security-sensitive issue signals found."],
            "evidence": signals,
            "recommended_actions": ["Keep security-sensitive issues in human review; do not request secrets publicly."] if signals else ["Continue normal triage."],
            "confidence": review["confidence"],
            "sources": signals,
        }
    if intent == "RELEASE_ANALYSIS":
        release_items = review["release_stability"]["release_related_issues"]
        return {
            "answer": "RHD checked issue wording and timing against synchronized releases. Correlation is not causation.",
            "key_findings": [f"Issue #{item['affected']['number']}: {item['reason']}" for item in release_items] or ["No release-correlation signals found."],
            "evidence": release_items,
            "recommended_actions": ["Verify suspected regressions against release notes and related PRs."],
            "confidence": review["confidence"],
            "sources": release_items,
        }
    if intent == "NEEDS_INFORMATION":
        incomplete = review["incomplete_reports"]
        return {
            "answer": f"RHD found {len(incomplete)} incomplete reports below the completeness threshold.",
            "key_findings": [f"Issue #{item['number']}: missing {', '.join(item['missing'])}" for item in incomplete],
            "evidence": incomplete,
            "recommended_actions": ["Request missing reproduction, environment, expected/actual behavior, or safe examples as applicable."],
            "confidence": review["confidence"],
            "sources": incomplete,
        }
    if intent == "PR_ANALYSIS":
        return {
            "answer": f"RHD found {review['pr_activity']['open']} open PRs across {review['pr_activity']['total']} synchronized pull requests.",
            "key_findings": [f"{review['pr_activity']['open']} open pull requests"],
            "evidence": [{"source_type": "repository analytics", "title": "PR Activity", "source_url": None}],
            "recommended_actions": ["Use issue investigations to inspect PR relationships for a specific issue."],
            "confidence": review["confidence"],
            "sources": [{"source_type": "repository analytics", "title": "PR Activity", "source_url": None}],
        }
    if intent == "ACTION_RECOMMENDATION":
        workload = review["maintainer_workload"]
        return {
            "answer": f"External actions remain human-gated. Current maintainer attention load is {workload['load']}.",
            "key_findings": [f"{key}: {value}" for key, value in workload["signals"].items()],
            "evidence": [{"source_type": "review queue", "title": "Pending recommendations", "source_url": None}],
            "recommended_actions": ["Open Review Queue before approving or executing any external GitHub action."],
            "confidence": "High",
            "sources": [{"source_type": "review queue", "title": "Pending recommendations", "source_url": None}],
        }
    results = search_repository_history(db, repository_id, question, top_k=5)
    return {
        "answer": "RHD searched repository-scoped indexed evidence.",
        "key_findings": [result.title for result in results] or ["No matching indexed repository evidence found."],
        "evidence": [result.__dict__ for result in results],
        "recommended_actions": ["Open the cited issue, PR, or release before acting."],
        "confidence": "Medium" if results else "Low",
        "sources": [result.__dict__ for result in results],
    }
