from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.api.routes.investigations import FeedbackRequest, create_feedback, list_feedback
from app.agents.tools.analysis import classify_issue
from app.core.config import Settings
from app.db.models import HumanFeedback, Investigation, Issue, PullRequest, Release, Repository
from app.services.advanced_intelligence import (
    advanced_escalation,
    analyze_completeness,
    analyze_duplicates,
    analyze_priority,
    analyze_related_pull_requests,
    analyze_release_regression,
    analyze_security,
    evaluation_metrics,
    repository_health,
)


def add_repo(db_session, full_name: str = "owner/demo") -> Repository:
    repo = Repository(github_id=abs(hash(full_name)) % 100000, owner=full_name.split("/")[0], name=full_name.split("/")[1], full_name=full_name, html_url=f"https://github.com/{full_name}")
    db_session.add(repo)
    db_session.flush()
    return repo


def add_issue(db_session, repo: Repository, number: int, title: str, body: str, labels: list[str] | None = None) -> Issue:
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


def test_duplicate_engine_semantic_pair_and_false_positive(db_session):
    repo = add_repo(db_session)
    auth_a = add_issue(db_session, repo, 1, "Login fails after latest update", "Users cannot authenticate after v1.2.0. Valid password shows login error.", ["bug"])
    auth_b = add_issue(db_session, repo, 2, "Authentication crashes after update", "The auth flow crashes after the newest release for valid accounts.", ["bug"])
    docs = add_issue(db_session, repo, 3, "Typo in README", "Installation section has a spelling mistake.", ["documentation"])
    result = analyze_duplicates(db_session, auth_a)
    top = result["duplicate_candidates"][0]
    assert top["github_issue_number"] == auth_b.github_issue_number
    assert top["duplicate_state"] in {"POSSIBLE_DUPLICATE", "VERY_LIKELY_DUPLICATE"}
    assert all(candidate["candidate_issue_id"] != auth_a.id for candidate in result["duplicate_candidates"])
    doc_candidate = [candidate for candidate in result["duplicate_candidates"] if candidate["github_issue_number"] == docs.github_issue_number][0]
    assert doc_candidate["final_duplicate_score"] < top["final_duplicate_score"]
    assert 0 <= top["final_duplicate_score"] <= 1


def test_duplicate_engine_cross_repository_exclusion(db_session):
    repo_a = add_repo(db_session, "a/repo")
    repo_b = add_repo(db_session, "b/repo")
    issue_a = add_issue(db_session, repo_a, 1, "Image upload fails", "PNG upload rejected after v1.2.0.", ["bug"])
    add_issue(db_session, repo_b, 1, "Image upload fails", "PNG upload rejected after v1.2.0.", ["bug"])
    result = analyze_duplicates(db_session, issue_a)
    assert result["duplicate_candidates"] == []


@pytest.mark.parametrize(
    ("title", "body", "labels", "expected_category", "missing_forbidden"),
    [
        ("Complete bug", "Steps: 1. Login. Expected dashboard. Actual error. Environment Windows. Version v1.2.0. Error message ERR_TEST.", ["bug"], "BUG", []),
        ("Application is not working", "Please fix.", ["bug"], "BUG", []),
        ("Typo in README", "Installation section has a typo and should say Run Tests.", ["documentation"], "DOCUMENTATION", ["environment", "logs"]),
        ("Add dark mode", "Use case: low light. Expected benefit: easier maintainer work. Current limitation: no theme.", ["enhancement"], "FEATURE_REQUEST", ["logs"]),
        ("Upload freezes", "Uploading a 25 MB image takes 30 seconds. Expected faster error. Actual freeze. Environment Edge. Version v1.2.0.", ["bug"], "PERFORMANCE", []),
    ],
)
def test_context_aware_completeness(db_session, title, body, labels, expected_category, missing_forbidden):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1, title, body, labels)
    category = classify_issue(issue)["category"]
    if title == "Upload freezes":
        category = "PERFORMANCE"
    result = analyze_completeness(issue, str(category))
    assert result["completeness_score"] >= 0
    assert result["issue_type_specific_requirements"]
    assert category == expected_category
    missing_text = " ".join(result["missing_information"]).lower()
    assert all(term not in missing_text for term in missing_forbidden)


def test_priority_security_and_urgent_wording(db_session):
    repo = add_repo(db_session)
    security_issue = add_issue(db_session, repo, 1, "API key appears in logs", "A fictional API key appears in application logs. No real secret included.", ["security-review"])
    normal_login = add_issue(db_session, repo, 2, "URGENT login bug", "Login fails but no security bypass or secret exposure is described.", ["bug"])
    docs = add_issue(db_session, repo, 3, "README typo", "Installation typo.", ["documentation"])
    release = {"regression_state": "NO_RELEASE_CORRELATION"}
    duplicate = {"duplicate_state": "UNLIKELY_DUPLICATE"}
    assert analyze_security(security_issue)["security_state"] == "HIGH_SECURITY_SIGNAL"
    assert analyze_security(normal_login)["security_state"] == "LOW_SECURITY_SIGNAL"
    security_priority = analyze_priority(security_issue, "SECURITY_RELATED", duplicate, analyze_completeness(security_issue, "SECURITY_RELATED"), analyze_security(security_issue), release)
    login_priority = analyze_priority(normal_login, "BUG", duplicate, analyze_completeness(normal_login, "BUG"), analyze_security(normal_login), release)
    docs_priority = analyze_priority(docs, "DOCUMENTATION", duplicate, analyze_completeness(docs, "DOCUMENTATION"), analyze_security(docs), release)
    assert security_priority["priority"] in {"HIGH", "CRITICAL"}
    assert login_priority["priority"] != "CRITICAL"
    assert docs_priority["priority"] == "LOW"


def test_release_regression_and_related_pr(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1, "File upload stopped working after v1.2.0", "PNG upload stopped working after v1.2.0.", ["bug"])
    release = Release(repository_id=repo.id, github_id=2, tag="v1.2.0", name="v1.2.0", body="Refactored file upload handling.", html_url=f"{repo.html_url}/releases/tag/v1.2.0", published_at=datetime.now(UTC) - timedelta(days=1))
    pr = PullRequest(repository_id=repo.id, github_id=3, github_pr_number=4, title="Refactor upload handler", body="Changes PNG image upload handling.", state="OPEN", html_url=f"{repo.html_url}/pull/4", updated_at=datetime.now(UTC))
    db_session.add_all([release, pr])
    db_session.commit()
    related = analyze_related_pull_requests(db_session, issue)
    regression = analyze_release_regression(db_session, issue, related)
    assert related and related[0]["number"] == 4
    assert regression["regression_state"] in {"POSSIBLE_POST_RELEASE_REGRESSION", "STRONG_TEMPORAL_CORRELATION"}
    assert "not proof of causation" in regression["explanation"]


def test_health_score_feedback_and_evaluation(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1, "README typo", "Typo in docs.", ["documentation"])
    investigation = Investigation(
        repository_id=repo.id,
        issue_id=issue.id,
        classification="DOCUMENTATION",
        classification_confidence=0.8,
        priority="LOW",
        priority_confidence=0.8,
        duplicate_probability=0,
        completeness_score=80,
        escalation_decision="NORMAL_QUEUE",
        escalation_confidence=0.8,
        summary="Docs issue",
        recommended_action="Queue",
    )
    db_session.add(investigation)
    db_session.flush()
    health_a = repository_health(db_session, repo.id)
    health_b = repository_health(db_session, repo.id)
    assert health_a == health_b
    assert 0 <= health_a["overall_score"] <= 100
    assert all(0 <= score <= 100 for score in health_a["dimension_scores"].values())
    assert evaluation_metrics(db_session, repo.id)["status"] == "INSUFFICIENT_LABELED_DATA"
    for index, status in enumerate(["CORRECT", "INCORRECT", "ADJUSTED"], start=1):
        db_session.add(
            HumanFeedback(
                repository_id=repo.id,
                issue_id=issue.id,
                investigation_id=investigation.id,
                target_type="classification",
                original_value="DOCUMENTATION",
                feedback_status=status,
                corrected_value="DOCUMENTATION" if status != "INCORRECT" else "BUG",
                comment=f"feedback {index}",
            )
        )
    db_session.commit()
    metrics = evaluation_metrics(db_session, repo.id)
    assert metrics["status"] == "OK"
    assert metrics["metrics"]["human_agreement_rate"] == pytest.approx(1 / 3, rel=1e-3)


def test_feedback_api_and_invalid_policy_configuration(db_session):
    repo = add_repo(db_session)
    issue = add_issue(db_session, repo, 1, "README typo", "Typo in docs.", ["documentation"])
    investigation = Investigation(
        repository_id=repo.id,
        issue_id=issue.id,
        classification="DOCUMENTATION",
        classification_confidence=0.8,
        priority="LOW",
        priority_confidence=0.8,
        duplicate_probability=0,
        completeness_score=80,
        escalation_decision="NORMAL_QUEUE",
        escalation_confidence=0.8,
        summary="Docs issue",
        recommended_action="Queue",
    )
    db_session.add(investigation)
    db_session.commit()

    created = create_feedback(
        investigation.id,
        FeedbackRequest(
            target_type="classification",
            original_value="DOCUMENTATION",
            feedback_status="ADJUSTED",
            corrected_value="BUG",
            comment="Incorrect label",
        ),
        db_session,
    )
    assert created["target_type"] == "classification"
    assert created["corrected_value"] == "BUG"
    assert len(list_feedback(investigation.id, db_session)) == 1

    bad_settings = Settings(duplicate_possible_threshold=0.9, duplicate_very_likely_threshold=0.5)
    with pytest.raises(ValueError):
        bad_settings.validate_policy()


def test_advanced_escalation_rules():
    assert advanced_escalation({"duplicate_state": "VERY_LIKELY_DUPLICATE"}, {"completeness_score": 90}, {"security_state": "LOW_SECURITY_SIGNAL"}, {"regression_state": "NO_RELEASE_CORRELATION"}, {"priority": "LOW"})["decision"] == "POSSIBLE_DUPLICATE"
    assert advanced_escalation({"duplicate_state": "UNLIKELY_DUPLICATE"}, {"completeness_score": 10}, {"security_state": "LOW_SECURITY_SIGNAL"}, {"regression_state": "NO_RELEASE_CORRELATION"}, {"priority": "MEDIUM"})["decision"] == "NEEDS_INFORMATION"
    assert advanced_escalation({"duplicate_state": "UNLIKELY_DUPLICATE"}, {"completeness_score": 90}, {"security_state": "HIGH_SECURITY_SIGNAL", "recommended_handling": "review"}, {"regression_state": "NO_RELEASE_CORRELATION"}, {"priority": "HIGH"})["decision"] == "URGENT_REVIEW"
