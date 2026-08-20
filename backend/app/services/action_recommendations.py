from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ActionRecommendation, Comment, HumanFeedback, Investigation, Issue, PullRequest, Repository
from app.github.client import GitHubAuthenticationError, GitHubNotFoundError, GitHubServiceError, GitHubCliService
from app.services.audit import log_audit_event

ALLOWED_ACTION_TYPES = {
    "NO_ACTION",
    "ADD_LABEL",
    "POST_COMMENT",
    "REQUEST_MORE_INFORMATION",
    "MARK_AS_POSSIBLE_DUPLICATE",
    "ESCALATE_FOR_MAINTAINER_REVIEW",
    "ESCALATE_FOR_SECURITY_REVIEW",
}
ALLOWED_STATUSES = {"PENDING", "APPROVED", "REJECTED", "EXECUTING", "EXECUTED", "FAILED", "CANCELLED"}
WRITE_ACTION_TYPES = {
    "ADD_LABEL",
    "POST_COMMENT",
    "REQUEST_MORE_INFORMATION",
    "MARK_AS_POSSIBLE_DUPLICATE",
    "ESCALATE_FOR_MAINTAINER_REVIEW",
    "ESCALATE_FOR_SECURITY_REVIEW",
}
SAFE_LABELS = {"possible-duplicate", "needs-info", "high-priority", "security-review", "documentation", "maintenance"}
COMMENT_ACTIONS = {"POST_COMMENT", "REQUEST_MORE_INFORMATION", "MARK_AS_POSSIBLE_DUPLICATE"}
MAINTAINER_ACTOR = "local-maintainer"


class ActionWorkflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    reason: str


def _signature(repository: Repository, issue: Issue, action_type: str, payload: dict[str, Any]) -> str:
    material = f"{repository.full_name}|{issue.github_issue_number}|{action_type}|{payload.get('label', '')}|{payload.get('comment_body', '')}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _safe_comment(text: str) -> bool:
    lowered = text.lower()
    for protective in [
        "please do not post passwords, api keys, access tokens, private credentials, or sensitive exploit details",
        "do not post passwords",
        "do not post api keys",
        "do not post access tokens",
    ]:
        lowered = lowered.replace(protective, "")
    forbidden = ["provide your password", "post your password", "post an api key", "provide an api key", "access token value", "private credential", "exploit details", "secret key"]
    return not any(term in lowered for term in forbidden)


def recommendation_dict(item: ActionRecommendation) -> dict[str, object]:
    issue = item.issue
    investigation = item.investigation
    return {
        "id": item.id,
        "repository_id": item.repository_id,
        "repository": issue.repository.full_name if issue and issue.repository else None,
        "issue_id": item.issue_id,
        "issue_number": issue.github_issue_number if issue else None,
        "issue_title": issue.title if issue else None,
        "issue_url": issue.html_url if issue else None,
        "investigation_id": item.investigation_id,
        "investigation_summary": investigation.summary if investigation else None,
        "priority": investigation.priority if investigation else None,
        "escalation": investigation.escalation_decision if investigation else None,
        "action_type": item.action_type,
        "status": item.status,
        "recommended_payload": item.recommended_payload,
        "reason": item.reason,
        "confidence": item.confidence,
        "policy_decision": item.policy_decision,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "approved_by": item.approved_by,
        "approved_at": item.approved_at,
        "rejected_by": item.rejected_by,
        "rejected_at": item.rejected_at,
        "executed_at": item.executed_at,
        "execution_status": item.execution_status,
        "execution_result": item.execution_result,
        "failure_reason": item.failure_reason,
        "security_signal": (item.recommended_payload or {}).get("security_signal"),
        "duplicate_state": (item.recommended_payload or {}).get("duplicate_state"),
    }


def _missing_info_comment(missing: list[str]) -> str:
    bullets = "\n".join(f"- {field}" for field in missing)
    return (
        "Thanks for reporting this. To help maintainers investigate, could you please provide:\n"
        f"{bullets}\n\n"
        "Please do not post passwords, API keys, access tokens, private credentials, or sensitive exploit details."
    )


def _duplicate_comment(candidate: dict[str, Any]) -> str:
    number = candidate["github_issue_number"]
    url = candidate["url"]
    return f"This may be related to Issue #{number}: {url}\n\nA maintainer should confirm whether it is a possible duplicate."


def generate_recommendation_for_investigation(db: Session, investigation: Investigation, analysis: dict[str, Any]) -> ActionRecommendation:
    issue = investigation.issue
    completeness = analysis["completeness"]
    duplicate = analysis["duplicate_analysis"]
    security = analysis["security_analysis"]
    priority = analysis["priority"]
    escalation = analysis["escalation"]
    release = analysis["release_regression_analysis"]

    action_type = "NO_ACTION"
    payload: dict[str, Any] = {
        "repository": issue.repository.full_name,
        "issue_number": issue.github_issue_number,
        "classification": investigation.classification,
        "priority": priority["priority"],
        "escalation": escalation["decision"],
        "security_signal": security["security_state"],
        "duplicate_state": duplicate["duplicate_state"],
        "release_regression": release["regression_state"],
    }
    reason = "No safe external action is recommended for this issue."
    confidence = float(escalation["confidence"])

    if security["security_state"] == "HIGH_SECURITY_SIGNAL":
        action_type = "ESCALATE_FOR_SECURITY_REVIEW"
        payload.update({"label": "security-review"})
        reason = "Security-sensitive report should be routed for private maintainer/security review."
        confidence = max(confidence, float(security["confidence"]))
    elif int(completeness["completeness_score"]) < settings.needs_info_comment_threshold:
        action_type = "REQUEST_MORE_INFORMATION"
        missing = [str(item) for item in completeness["missing_information"]]
        payload.update({"comment_body": _missing_info_comment(missing), "missing_information": missing})
        reason = "The issue is missing required fields for its issue type."
    elif duplicate["duplicate_state"] in {"POSSIBLE_DUPLICATE", "VERY_LIKELY_DUPLICATE"} and float(duplicate["top_score"]) >= settings.duplicate_comment_threshold:
        candidate = duplicate["duplicate_candidates"][0]
        action_type = "MARK_AS_POSSIBLE_DUPLICATE"
        payload.update({"comment_body": _duplicate_comment(candidate), "duplicate_candidate": candidate})
        reason = "The issue has a verified similar report in the same repository."
        confidence = float(duplicate["top_score"])
    elif investigation.escalation_decision == "MAINTAINER_REVIEW" or priority["priority"] in {"HIGH", "CRITICAL"}:
        action_type = "ESCALATE_FOR_MAINTAINER_REVIEW"
        payload.update({"label": "high-priority"})
        reason = "The issue has high-priority repository signals and should enter maintainer review."
    elif investigation.classification == "DOCUMENTATION":
        action_type = "NO_ACTION"
        reason = "Low-risk documentation issue can remain in the normal queue without noisy automation."

    recommendation = ActionRecommendation(
        repository_id=investigation.repository_id,
        issue_id=investigation.issue_id,
        investigation_id=investigation.id,
        action_type=action_type,
        status="PENDING",
        recommended_payload=payload,
        reason=reason,
        confidence=round(confidence, 4),
        policy_decision="PENDING_REVIEW",
        execution_signature=_signature(issue.repository, issue, action_type, payload),
    )
    db.add(recommendation)
    db.flush()
    log_audit_event(
        db,
        "RECOMMENDATION_CREATED",
        f"Created {action_type} recommendation for issue #{issue.github_issue_number}.",
        repository_id=investigation.repository_id,
        issue_id=investigation.issue_id,
        investigation_id=investigation.id,
        action_recommendation_id=recommendation.id,
        metadata={"action_type": action_type, "confidence": recommendation.confidence},
    )
    return recommendation


def validate_policy(db: Session, recommendation: ActionRecommendation) -> PolicyResult:
    issue = recommendation.issue
    repository = issue.repository
    payload = recommendation.recommended_payload or {}
    action_type = recommendation.action_type

    if action_type not in ALLOWED_ACTION_TYPES:
        return PolicyResult("BLOCKED", "Unsupported action type")
    if action_type == "NO_ACTION":
        return PolicyResult("ALLOWED", "No external write will be executed")
    if action_type in WRITE_ACTION_TYPES and repository.full_name != settings.allowed_write_repository:
        return PolicyResult("BLOCKED", "Repository is not in the write allow-list")
    if settings.require_human_approval and recommendation.status not in {"APPROVED", "EXECUTING"}:
        return PolicyResult("BLOCKED", "Human approval is required before execution")
    if action_type in COMMENT_ACTIONS:
        body = str(payload.get("comment_body", ""))
        if not settings.allow_comment_actions:
            return PolicyResult("BLOCKED", "Comment actions are disabled by policy")
        if not body.strip():
            return PolicyResult("BLOCKED", "Comment body is empty")
        if len(body) > settings.max_comment_length:
            return PolicyResult("BLOCKED", "Comment exceeds policy length")
        if not _safe_comment(body):
            return PolicyResult("BLOCKED", "Comment contains unsafe sensitive-detail wording")
        candidate = payload.get("duplicate_candidate")
        if action_type == "MARK_AS_POSSIBLE_DUPLICATE":
            if not isinstance(candidate, dict) or not db.get(Issue, int(candidate.get("candidate_issue_id", 0))):
                return PolicyResult("BLOCKED", "Duplicate target issue is not verified")
    if action_type in {"ADD_LABEL", "ESCALATE_FOR_MAINTAINER_REVIEW", "ESCALATE_FOR_SECURITY_REVIEW"}:
        label = str(payload.get("label", ""))
        if not settings.allow_label_actions:
            return PolicyResult("BLOCKED", "Label actions are disabled by policy")
        if label not in SAFE_LABELS:
            return PolicyResult("BLOCKED", "Label is not allowed by policy")
        if action_type == "ESCALATE_FOR_SECURITY_REVIEW" and settings.security_actions_require_manual_review and recommendation.status != "APPROVED":
            return PolicyResult("BLOCKED", "Security actions require manual approval")
    executed = (
        db.query(ActionRecommendation)
        .filter(
            ActionRecommendation.id != recommendation.id,
            ActionRecommendation.execution_signature == recommendation.execution_signature,
            ActionRecommendation.status == "EXECUTED",
        )
        .first()
    )
    if executed:
        return PolicyResult("BLOCKED", "Equivalent action has already executed")
    return PolicyResult("ALLOWED", "Policy validation passed")


def approve_recommendation(db: Session, recommendation: ActionRecommendation, actor: str = MAINTAINER_ACTOR) -> ActionRecommendation:
    if recommendation.status != "PENDING":
        raise ActionWorkflowError(f"Cannot approve recommendation in {recommendation.status} status")
    recommendation.status = "APPROVED"
    recommendation.approved_by = actor
    recommendation.approved_at = datetime.now(UTC)
    recommendation.policy_decision = "APPROVED_PENDING_EXECUTION"
    log_audit_event(
        db,
        "RECOMMENDATION_APPROVED",
        f"Approved {recommendation.action_type} recommendation.",
        actor=actor,
        repository_id=recommendation.repository_id,
        issue_id=recommendation.issue_id,
        investigation_id=recommendation.investigation_id,
        action_recommendation_id=recommendation.id,
    )
    return recommendation


def reject_recommendation(db: Session, recommendation: ActionRecommendation, actor: str = MAINTAINER_ACTOR, reason: str | None = None) -> ActionRecommendation:
    if recommendation.status not in {"PENDING", "APPROVED", "FAILED"}:
        raise ActionWorkflowError(f"Cannot reject recommendation in {recommendation.status} status")
    recommendation.status = "REJECTED"
    recommendation.rejected_by = actor
    recommendation.rejected_at = datetime.now(UTC)
    recommendation.failure_reason = reason
    recommendation.policy_decision = "REJECTED_BY_MAINTAINER"
    log_audit_event(
        db,
        "RECOMMENDATION_REJECTED",
        f"Rejected {recommendation.action_type} recommendation.",
        actor=actor,
        repository_id=recommendation.repository_id,
        issue_id=recommendation.issue_id,
        investigation_id=recommendation.investigation_id,
        action_recommendation_id=recommendation.id,
        metadata={"reason": reason or ""},
    )
    return recommendation


def _execute_label(service: GitHubCliService, repository: Repository, issue: Issue, label: str) -> dict[str, Any]:
    if label in (issue.labels or []):
        return {"status": "skipped", "reason": "label already present", "label": label}
    service.get_label(repository.full_name, label)
    result = service.add_issue_label(repository.full_name, issue.github_issue_number, label)
    return {"status": "success", "label": label, "github_response": result}


def _execute_comment(db: Session, service: GitHubCliService, repository: Repository, issue: Issue, body: str) -> dict[str, Any]:
    existing = db.query(Comment).filter_by(repository_id=repository.id, issue_id=issue.id).all()
    if any((comment.body or "").strip() == body.strip() for comment in existing):
        return {"status": "skipped", "reason": "identical synchronized comment already exists"}
    for comment in service.get_issue_comments(repository.full_name, issue.github_issue_number):
        if str(comment.get("body", "")).strip() == body.strip():
            return {"status": "skipped", "reason": "identical GitHub comment already exists"}
    result = service.post_issue_comment(repository.full_name, issue.github_issue_number, body)
    return {"status": "success", "github_response": result}


def execute_recommendation(db: Session, recommendation: ActionRecommendation, service: GitHubCliService | None = None, actor: str = MAINTAINER_ACTOR) -> ActionRecommendation:
    if recommendation.status != "APPROVED":
        raise ActionWorkflowError("Recommendation must be approved before execution")
    policy = validate_policy(db, recommendation)
    if policy.decision != "ALLOWED":
        recommendation.status = "FAILED"
        recommendation.execution_status = "POLICY_BLOCKED"
        recommendation.failure_reason = policy.reason
        recommendation.policy_decision = "BLOCKED"
        log_audit_event(
            db,
            "POLICY_BLOCKED_ACTION",
            policy.reason,
            actor=actor,
            repository_id=recommendation.repository_id,
            issue_id=recommendation.issue_id,
            investigation_id=recommendation.investigation_id,
            action_recommendation_id=recommendation.id,
        )
        return recommendation

    issue = recommendation.issue
    repository = issue.repository
    payload = recommendation.recommended_payload or {}
    service = service or GitHubCliService()
    recommendation.status = "EXECUTING"
    recommendation.policy_decision = "ALLOWED"
    try:
        if recommendation.action_type == "NO_ACTION":
            result = {"status": "skipped", "reason": "No external action requested"}
        elif recommendation.action_type in {"ADD_LABEL", "ESCALATE_FOR_MAINTAINER_REVIEW", "ESCALATE_FOR_SECURITY_REVIEW"}:
            result = _execute_label(service, repository, issue, str(payload["label"]))
        elif recommendation.action_type in COMMENT_ACTIONS:
            result = _execute_comment(db, service, repository, issue, str(payload["comment_body"]))
        else:
            raise ActionWorkflowError("Unsupported execution action")
        recommendation.status = "EXECUTED"
        recommendation.execution_status = str(result.get("status", "success")).upper()
        recommendation.execution_result = result
        recommendation.executed_at = datetime.now(UTC)
        log_audit_event(
            db,
            "GITHUB_ACTION_EXECUTED",
            f"Executed {recommendation.action_type} for issue #{issue.github_issue_number}.",
            actor=actor,
            repository_id=recommendation.repository_id,
            issue_id=recommendation.issue_id,
            investigation_id=recommendation.investigation_id,
            action_recommendation_id=recommendation.id,
            metadata={"result": recommendation.execution_status},
        )
    except (GitHubAuthenticationError, GitHubNotFoundError, GitHubServiceError, ActionWorkflowError, KeyError) as exc:
        recommendation.status = "FAILED"
        recommendation.execution_status = "FAILED"
        recommendation.failure_reason = str(exc)
        recommendation.executed_at = datetime.now(UTC)
        log_audit_event(
            db,
            "GITHUB_ACTION_FAILED",
            f"Failed {recommendation.action_type}: {str(exc)[:300]}",
            actor=actor,
            repository_id=recommendation.repository_id,
            issue_id=recommendation.issue_id,
            investigation_id=recommendation.investigation_id,
            action_recommendation_id=recommendation.id,
        )
    return recommendation


def issue_action_history(db: Session, issue_id: int) -> dict[str, object]:
    recommendations = db.query(ActionRecommendation).filter_by(issue_id=issue_id).order_by(ActionRecommendation.created_at.desc()).all()
    feedback = db.query(HumanFeedback).filter_by(issue_id=issue_id).order_by(HumanFeedback.created_at.desc()).all()
    return {
        "recommendations": [recommendation_dict(item) for item in recommendations],
        "feedback": [
            {
                "id": item.id,
                "target_type": item.target_type,
                "original_value": item.original_value,
                "feedback_status": item.feedback_status,
                "corrected_value": item.corrected_value,
                "comment": item.comment,
                "created_at": item.created_at,
            }
            for item in feedback
        ],
    }
