from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.db.models import ActionRecommendation, AuditLogEvent, Comment, Investigation, Issue, Repository
from app.services.action_recommendations import (
    ActionWorkflowError,
    approve_recommendation,
    execute_recommendation,
    generate_recommendation_for_investigation,
    reject_recommendation,
    validate_policy,
)


def add_repo(db_session, full_name: str = "romil569/RepoGuardian-Demo") -> Repository:
    repo = Repository(github_id=abs(hash(full_name)) % 100000, owner=full_name.split("/")[0], name=full_name.split("/")[1], full_name=full_name, html_url=f"https://github.com/{full_name}")
    db_session.add(repo)
    db_session.flush()
    return repo


def add_issue(db_session, repo: Repository, number: int, title: str = "Application is not working", body: str = "Please fix.", labels: list[str] | None = None) -> Issue:
    issue = Issue(
        repository_id=repo.id,
        github_id=number,
        github_issue_number=number,
        title=title,
        body=body,
        state="OPEN",
        labels=labels or [],
        html_url=f"{repo.html_url}/issues/{number}",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(issue)
    db_session.flush()
    return issue


def add_investigation(db_session, repo: Repository, issue: Issue, classification: str = "BUG", priority: str = "LOW", escalation: str = "NEEDS_INFORMATION") -> Investigation:
    investigation = Investigation(
        repository_id=repo.id,
        issue_id=issue.id,
        classification=classification,
        classification_confidence=0.8,
        priority=priority,
        priority_confidence=0.8,
        duplicate_probability=0.0,
        completeness_score=10,
        escalation_decision=escalation,
        escalation_confidence=0.9,
        summary="Test investigation",
        recommended_action="Test action",
    )
    db_session.add(investigation)
    db_session.flush()
    return investigation


def analysis_payload(action: str) -> dict[str, object]:
    base = {
        "completeness": {"completeness_score": 90, "missing_information": []},
        "duplicate_analysis": {"duplicate_state": "UNLIKELY_DUPLICATE", "top_score": 0.0, "duplicate_candidates": []},
        "security_analysis": {"security_state": "LOW_SECURITY_SIGNAL", "confidence": 0.08},
        "priority": {"priority": "LOW"},
        "escalation": {"decision": "NORMAL_QUEUE", "confidence": 0.74},
        "release_regression_analysis": {"regression_state": "NO_RELEASE_CORRELATION"},
    }
    if action == "needs_info":
        base["completeness"] = {"completeness_score": 0, "missing_information": ["steps to reproduce", "error message/logs"]}
        base["escalation"] = {"decision": "NEEDS_INFORMATION", "confidence": 0.9}
    if action == "duplicate":
        candidate = add_issue._candidate  # type: ignore[attr-defined]
        base["duplicate_analysis"] = {
            "duplicate_state": "POSSIBLE_DUPLICATE",
            "top_score": 0.62,
            "duplicate_candidates": [
                {"candidate_issue_id": candidate.id, "github_issue_number": candidate.github_issue_number, "url": candidate.html_url, "title": candidate.title}
            ],
        }
        base["escalation"] = {"decision": "POSSIBLE_DUPLICATE", "confidence": 0.82}
    if action == "security":
        base["security_analysis"] = {"security_state": "HIGH_SECURITY_SIGNAL", "confidence": 0.86}
        base["priority"] = {"priority": "HIGH"}
        base["escalation"] = {"decision": "URGENT_REVIEW", "confidence": 0.92}
    return base


class FakeGitHub:
    def __init__(self, fail: str | None = None):
        self.fail = fail
        self.labels: list[str] = []
        self.comments: list[str] = []

    def get_label(self, full_name, label):
        if self.fail == "404":
            from app.github.client import GitHubNotFoundError

            raise GitHubNotFoundError("label missing")
        return {"name": label}

    def add_issue_label(self, full_name, number, label):
        if self.fail == "403":
            from app.github.client import GitHubServiceError

            raise GitHubServiceError("403 permission denied")
        self.labels.append(label)
        return [{"name": label}]

    def get_issue_comments(self, full_name, number):
        if self.fail == "rate":
            from app.github.client import GitHubServiceError

            raise GitHubServiceError("rate limit exceeded")
        return [{"body": body} for body in self.comments]

    def post_issue_comment(self, full_name, number, body):
        if self.fail == "network":
            from app.github.client import GitHubServiceError

            raise GitHubServiceError("network failure")
        self.comments.append(body)
        return {"id": 123, "html_url": f"https://github.com/{full_name}/issues/{number}#issuecomment-123"}


def test_recommendation_quality_for_key_scenarios(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1)
    investigation = add_investigation(db_session, repo, issue)
    add_issue._candidate = add_issue(db_session, repo, 2, "Login fails after latest update")  # type: ignore[attr-defined]

    needs_info = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("needs_info"))
    assert needs_info.action_type == "REQUEST_MORE_INFORMATION"
    assert "steps to reproduce" in needs_info.recommended_payload["comment_body"]

    duplicate = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("duplicate"))
    assert duplicate.action_type == "MARK_AS_POSSIBLE_DUPLICATE"
    assert "may be related" in duplicate.recommended_payload["comment_body"]

    security = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("security"))
    assert security.action_type == "ESCALATE_FOR_SECURITY_REVIEW"
    assert security.recommended_payload["label"] == "security-review"

    docs = add_investigation(db_session, repo, issue, classification="DOCUMENTATION", priority="LOW", escalation="NORMAL_QUEUE")
    no_action = generate_recommendation_for_investigation(db_session, docs, analysis_payload("normal"))
    assert no_action.action_type == "NO_ACTION"


def test_approval_rejection_and_invalid_transitions(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1)
    investigation = add_investigation(db_session, repo, issue)
    recommendation = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("needs_info"))

    with pytest.raises(ActionWorkflowError):
        execute_recommendation(db_session, recommendation, FakeGitHub())

    approve_recommendation(db_session, recommendation)
    assert recommendation.status == "APPROVED"
    with pytest.raises(ActionWorkflowError):
        approve_recommendation(db_session, recommendation)

    rejected = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("needs_info"))
    reject_recommendation(db_session, rejected, reason="Not useful")
    assert rejected.status == "REJECTED"
    with pytest.raises(ActionWorkflowError):
        execute_recommendation(db_session, rejected, FakeGitHub())


def test_policy_and_mocked_github_actions(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1)
    investigation = add_investigation(db_session, repo, issue)
    recommendation = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("needs_info"))
    approve_recommendation(db_session, recommendation)
    service = FakeGitHub()
    execute_recommendation(db_session, recommendation, service)
    assert recommendation.status == "EXECUTED"
    assert service.comments

    duplicate = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("needs_info"))
    approve_recommendation(db_session, duplicate)
    execute_recommendation(db_session, duplicate, service)
    assert duplicate.status == "FAILED"
    assert duplicate.execution_status == "POLICY_BLOCKED"

    issue_with_existing = add_issue(db_session, repo, 2)
    investigation_existing = add_investigation(db_session, repo, issue_with_existing)
    existing = generate_recommendation_for_investigation(db_session, investigation_existing, analysis_payload("needs_info"))
    approve_recommendation(db_session, existing)
    db_session.add(Comment(repository_id=repo.id, issue_id=issue_with_existing.id, github_id=555, body=existing.recommended_payload["comment_body"]))
    execute_recommendation(db_session, existing, service)
    assert existing.execution_result["status"] == "skipped"

    bad_repo = add_repo(db_session, "someone/else")
    bad_issue = add_issue(db_session, bad_repo, 3)
    bad_investigation = add_investigation(db_session, bad_repo, bad_issue)
    blocked = generate_recommendation_for_investigation(db_session, bad_investigation, analysis_payload("needs_info"))
    approve_recommendation(db_session, blocked)
    assert validate_policy(db_session, blocked).decision == "BLOCKED"
    execute_recommendation(db_session, blocked, FakeGitHub())
    assert blocked.status == "FAILED"
    assert blocked.execution_status == "POLICY_BLOCKED"


@pytest.mark.parametrize("failure", ["403", "404", "rate", "network"])
def test_github_action_failures_are_recorded(db_session, failure):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1)
    investigation = add_investigation(db_session, repo, issue)
    recommendation = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("security" if failure in {"403", "404"} else "needs_info"))
    approve_recommendation(db_session, recommendation)
    execute_recommendation(db_session, recommendation, FakeGitHub(fail=failure))
    assert recommendation.status == "FAILED"
    assert recommendation.failure_reason


def test_audit_log_and_settings_validation(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1)
    investigation = add_investigation(db_session, repo, issue)
    recommendation = generate_recommendation_for_investigation(db_session, investigation, analysis_payload("needs_info"))
    approve_recommendation(db_session, recommendation)
    reject_recommendation(db_session, recommendation, reason="demo rejection")

    events = db_session.query(AuditLogEvent).all()
    assert {event.event_type for event in events} >= {"RECOMMENDATION_CREATED", "RECOMMENDATION_APPROVED", "RECOMMENDATION_REJECTED"}
    assert all("gho_" not in event.safe_summary and "sk-" not in event.safe_summary for event in events)

    bad_settings = Settings(allowed_write_repository="not-a-repo")
    with pytest.raises(ValueError):
        bad_settings.validate_policy()

    bad_ai_mode = Settings(ai_provider_mode="unsafe")
    with pytest.raises(ValueError):
        bad_ai_mode.validate_policy()
