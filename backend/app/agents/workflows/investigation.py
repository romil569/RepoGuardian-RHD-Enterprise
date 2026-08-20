from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.orm import Session

from app.agents.tools.analysis import (
    classify_issue,
    get_recent_releases,
)
from app.core.config import settings
from app.db.models import AgentExecutionStep, EscalationDecision, Investigation, InvestigationEvidence, Issue
from app.rag.retriever import search_repository_history
from app.services.action_recommendations import generate_recommendation_for_investigation, recommendation_dict
from app.services.advanced_intelligence import (
    advanced_escalation,
    analyze_completeness,
    analyze_duplicates,
    analyze_priority,
    analyze_related_pull_requests,
    analyze_release_regression,
    analyze_security,
    compute_telemetry,
)
from app.services.audit import log_audit_event
from app.services.evidence import filter_valid_evidence


class InvestigationOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.trace: list[dict[str, object]] = []

    def _step(self, name: str, status: str, summary: str, result: dict[str, object] | None = None, start: float | None = None) -> None:
        duration = int((perf_counter() - start) * 1000) if start else 0
        self.trace.append(
            {
                "step_number": len(self.trace) + 1,
                "tool_name": name,
                "status": status,
                "duration_ms": duration,
                "summary": summary,
                "result": result or {},
            }
        )

    def investigate_issue(self, issue_id: int) -> dict[str, object]:
        start = perf_counter()
        issue = self.db.get(Issue, issue_id)
        if not issue:
            raise ValueError("Issue not found")
        log_audit_event(
            self.db,
            "INVESTIGATION_STARTED",
            f"Started investigation for issue #{issue.github_issue_number}.",
            repository_id=issue.repository_id,
            issue_id=issue.id,
        )
        self._step("get_issue_details", "SUCCESS", f"Loaded issue #{issue.github_issue_number}", {"github_number": issue.github_issue_number}, start)

        start = perf_counter()
        classification = classify_issue(issue)
        self._step("classify_issue", "SUCCESS", str(classification["category"]), classification, start)

        start = perf_counter()
        completeness = analyze_completeness(issue, str(classification["category"]))
        self._step("check_issue_completeness", "SUCCESS", f"score {completeness['completeness_score']}", completeness, start)

        query = f"{issue.title}\n{issue.body or ''}"
        start = perf_counter()
        context = search_repository_history(self.db, issue.repository_id, query, top_k=5)
        self._step("search_repository_history", "SUCCESS", f"{len(context)} results", {"count": len(context)}, start)

        start = perf_counter()
        duplicate_analysis = analyze_duplicates(self.db, issue, limit=5)
        similar = duplicate_analysis["duplicate_candidates"]
        duplicate_probability = float(duplicate_analysis["top_score"])
        self._step("search_similar_issues", "SUCCESS", f"{len(similar)} candidates", duplicate_analysis, start)

        start = perf_counter()
        related_prs = analyze_related_pull_requests(self.db, issue)
        self._step("get_related_pull_requests", "SUCCESS", f"{len(related_prs)} related PRs", {"count": len(related_prs)}, start)

        start = perf_counter()
        releases = get_recent_releases(self.db, issue.repository_id)
        self._step("get_recent_releases", "SUCCESS", f"{len(releases)} releases", {"count": len(releases)}, start)

        start = perf_counter()
        security = analyze_security(issue)
        self._step("detect_security_signal", "SUCCESS", str(security["security_state"]), security, start)

        start = perf_counter()
        release_regression = analyze_release_regression(self.db, issue, related_prs)
        self._step("analyze_release_regression", "SUCCESS", str(release_regression["regression_state"]), release_regression, start)

        start = perf_counter()
        priority = analyze_priority(issue, str(classification["category"]), duplicate_analysis, completeness, security, release_regression)
        self._step("calculate_priority", "SUCCESS", str(priority["level"]), priority, start)

        start = perf_counter()
        escalation = advanced_escalation(duplicate_analysis, completeness, security, release_regression, priority)
        self._step("determine_escalation", "SUCCESS", str(escalation["decision"]), escalation, start)

        raw_evidence = [
            {
                "repository_id": item.repository_id,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "github_number": item.github_number,
                "title": item.title,
                "source_url": item.source_url,
                "retrieval_score": item.relevance_score,
                "why_relevant": "Retrieved from synchronized repository history for this issue investigation.",
            }
            for item in context[:4]
        ]
        pr_by_number = {pr.github_pr_number: pr for pr in issue.repository.pull_requests}
        for pr_item in related_prs[:2]:
            pr = pr_by_number.get(int(pr_item["number"]))
            if not pr:
                continue
            raw_evidence.append(
                {
                    "repository_id": pr.repository_id,
                    "source_type": "PULL_REQUEST",
                    "source_id": pr.id,
                    "github_number": pr.github_pr_number,
                    "title": pr.title,
                    "source_url": pr.html_url,
                    "retrieval_score": float(pr_item["relevance_score"]),
                    "why_relevant": str(pr_item["why_relevant"]),
                }
            )
        valid_evidence, rejected = filter_valid_evidence(self.db, raw_evidence)
        self._step("validate_evidence", "SUCCESS", f"{len(valid_evidence)} valid, {len(rejected)} rejected", {"rejected": len(rejected)})
        if not valid_evidence:
            self._step("collect_evidence", "INSUFFICIENT_EVIDENCE", "No verified evidence was available")

        summary = f"Issue #{issue.github_issue_number} is classified as {classification['category']} with priority {priority['level']}."
        if not settings.openai_api_key:
            summary += " Live AI provider is not configured; deterministic repository tools produced this assessment."
        investigation = Investigation(
            repository_id=issue.repository_id,
            issue_id=issue.id,
            status="COMPLETED",
            classification=str(classification["category"]),
            classification_confidence=float(classification["confidence"]),
            priority=str(priority["level"]),
            priority_confidence=float(priority["confidence"]),
            duplicate_probability=min(duplicate_probability, 1.0),
            completeness_score=int(completeness["score"]),
            escalation_decision=str(escalation["decision"]),
            escalation_confidence=float(escalation["confidence"]),
            summary=summary,
            recommended_action=str(escalation["recommended_action"]),
            completed_at=datetime.now(UTC),
        )
        self.db.add(investigation)
        self.db.flush()
        self.db.add(
            EscalationDecision(
                investigation_id=investigation.id,
                repository_id=issue.repository_id,
                decision=str(escalation["decision"]),
                confidence=float(escalation["confidence"]),
                reason_codes=list(escalation["reason_codes"]),
                recommended_action=str(escalation["recommended_action"]),
            )
        )
        for item in valid_evidence:
            self.db.add(InvestigationEvidence(investigation_id=investigation.id, **item))
        for step in self.trace:
            self.db.add(AgentExecutionStep(investigation_id=investigation.id, **step))
        issue.analysis_status = "ANALYZED"
        self.db.commit()
        self.db.refresh(investigation)
        telemetry = compute_telemetry(investigation, len(valid_evidence))
        recommendation = generate_recommendation_for_investigation(
            self.db,
            investigation,
            {
                "completeness": completeness,
                "duplicate_analysis": duplicate_analysis,
                "security_analysis": security,
                "priority": priority,
                "escalation": escalation,
                "release_regression_analysis": release_regression,
            },
        )
        log_audit_event(
            self.db,
            "INVESTIGATION_COMPLETED",
            f"Completed investigation for issue #{issue.github_issue_number} with escalation {escalation['decision']}.",
            repository_id=issue.repository_id,
            issue_id=issue.id,
            investigation_id=investigation.id,
            metadata={"priority": priority["priority"], "escalation": escalation["decision"]},
        )
        self.db.commit()
        self.db.refresh(recommendation)

        return {
            "investigation_id": investigation.id,
            "issue": issue_to_dict(issue),
            "classification": classification,
            "completeness": completeness,
            "completeness_analysis": completeness,
            "duplicate_analysis": duplicate_analysis,
            "similar_issues": similar,
            "repository_context": [result.__dict__ for result in context],
            "related_pull_requests": related_prs,
            "recent_releases": [release_to_dict(release) for release in releases],
            "security_analysis": security,
            "release_regression_analysis": release_regression,
            "priority": priority,
            "priority_analysis": priority,
            "escalation": escalation,
            "evidence": valid_evidence,
            "recommended_action": investigation.recommended_action,
            "summary": investigation.summary,
            "investigation_trace": self.trace,
            "telemetry": telemetry,
            "action_recommendations": [recommendation_dict(recommendation)],
        }


def issue_to_dict(issue: Issue) -> dict[str, object]:
    return {
        "id": issue.id,
        "repository_id": issue.repository_id,
        "number": issue.github_issue_number,
        "title": issue.title,
        "body": issue.body,
        "state": issue.state,
        "author": issue.author,
        "labels": issue.labels,
        "html_url": issue.html_url,
        "analysis_status": issue.analysis_status,
    }


def pr_to_dict(pr) -> dict[str, object]:
    return {"id": pr.id, "number": pr.github_pr_number, "title": pr.title, "state": pr.state, "html_url": pr.html_url}


def release_to_dict(release) -> dict[str, object]:
    return {"id": release.id, "tag": release.tag, "name": release.name, "html_url": release.html_url, "body": release.body}
