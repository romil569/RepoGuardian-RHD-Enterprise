from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.models import ActionRecommendation, IndexedDocument, Investigation, Issue, PullRequest, Release, Repository
from app.services.action_recommendations import approve_recommendation, validate_policy
from app.services.rhd import answer_question, duplicate_clusters, full_repository_review, maintainer_workload, parse_repository_input, repository_access_mode, route_intent


def add_repo(db_session, full_name: str = "romil569/RepoGuardian-Demo") -> Repository:
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


def add_investigation(db_session, repo: Repository, issue: Issue, priority: str = "HIGH", escalation: str = "MAINTAINER_REVIEW") -> Investigation:
    investigation = Investigation(
        repository_id=repo.id,
        issue_id=issue.id,
        classification="BUG",
        classification_confidence=0.82,
        priority=priority,
        priority_confidence=0.8,
        duplicate_probability=0.52 if escalation == "POSSIBLE_DUPLICATE" else 0.0,
        completeness_score=25 if escalation == "NEEDS_INFORMATION" else 90,
        escalation_decision=escalation,
        escalation_confidence=0.8,
        summary="Repository-grounded investigation",
        recommended_action="Review issue",
    )
    db_session.add(investigation)
    db_session.flush()
    return investigation


def seed_repository(db_session, full_name: str = "romil569/RepoGuardian-Demo") -> Repository:
    repo = add_repo(db_session, full_name)
    issue_a = add_issue(db_session, repo, 1, "Image upload fails after v1.2.0", "Steps: upload PNG. Expected success. Actual upload error after v1.2.0. Environment Windows.", ["bug"])
    issue_b = add_issue(db_session, repo, 2, "PNG upload error after latest release", "Image upload fails after recent release with error message.", ["bug"])
    issue_c = add_issue(db_session, repo, 3, "API key appears in logs", "A fictional API key appears in application logs. No real secret included.", ["security-review"])
    add_investigation(db_session, repo, issue_a, "HIGH", "POSSIBLE_DUPLICATE")
    add_investigation(db_session, repo, issue_b, "HIGH", "POSSIBLE_DUPLICATE")
    investigation_c = add_investigation(db_session, repo, issue_c, "HIGH", "URGENT_REVIEW")
    db_session.add(PullRequest(repository_id=repo.id, github_id=10, github_pr_number=4, title="Refactor upload handler", body="Changes PNG upload handling.", state="OPEN", html_url=f"{repo.html_url}/pull/4", created_at=datetime.now(UTC), updated_at=datetime.now(UTC)))
    db_session.add(Release(repository_id=repo.id, github_id=11, tag="v1.2.0", name="v1.2.0", body="Upload handler changes.", html_url=f"{repo.html_url}/releases/tag/v1.2.0", published_at=datetime.now(UTC)))
    db_session.add(IndexedDocument(repository_id=repo.id, source_type="ISSUE", source_id=issue_a.id, github_number=1, title=issue_a.title, source_url=issue_a.html_url, text=issue_a.body or "", token_vector={"upload": 1.0}))
    db_session.add(IndexedDocument(repository_id=repo.id, source_type="ISSUE", source_id=issue_c.id, github_number=3, title=issue_c.title, source_url=issue_c.html_url, text=issue_c.body or "", token_vector={"security": 1.0}))
    db_session.add(
        ActionRecommendation(
            repository_id=repo.id,
            issue_id=issue_c.id,
            investigation_id=investigation_c.id,
            action_type="ESCALATE_FOR_SECURITY_REVIEW",
            status="PENDING",
            recommended_payload={"label": "security-review"},
            reason="Security-sensitive report should be routed for review.",
            confidence=0.9,
            policy_decision="PENDING_REVIEW",
        )
    )
    db_session.commit()
    return repo


def test_repository_url_parsing_and_invalid_url():
    assert parse_repository_input("https://github.com/openai/codex").full_name == "openai/codex"
    assert parse_repository_input("owner/repository").html_url == "https://github.com/owner/repository"
    with pytest.raises(ValueError):
        parse_repository_input("https://gitlab.com/owner/repository")


def test_public_repository_read_only_mode_and_policy_preservation(db_session):
    repo = seed_repository(db_session, "someone/public-demo")
    assert repository_access_mode(repo) == "READ_ONLY_PUBLIC"
    recommendation = db_session.query(ActionRecommendation).filter_by(repository_id=repo.id).one()
    approve_recommendation(db_session, recommendation)
    assert validate_policy(db_session, recommendation).decision == "BLOCKED"


@pytest.mark.parametrize(
    ("query", "intent"),
    [
        ("Give me a full review", "FULL_REPOSITORY_REVIEW"),
        ("Show duplicate issues", "DUPLICATE_ANALYSIS"),
        ("Which issues are security-sensitive?", "SECURITY_REVIEW"),
        ("What happened after v1.2.0?", "RELEASE_ANALYSIS"),
        ("Which issues need more information?", "NEEDS_INFORMATION"),
        ("What should I fix first?", "TOP_PRIORITIES"),
    ],
)
def test_rhd_intent_router(query, intent):
    assert route_intent(query) == intent


def test_full_repository_review_top_actions_and_grounding(db_session):
    repo = seed_repository(db_session)
    review = full_repository_review(db_session, repo.id)
    assert review["repository"]["full_name"] == repo.full_name
    assert review["executive_assessment"]["health_score"] >= 0
    assert review["recommended_action_plan"]
    assert review["evidence"]
    assert all("affected" in item and item["evidence"] for item in review["recommended_action_plan"])


def test_rhd_query_trace_source_grounding_and_refusal(db_session):
    repo = seed_repository(db_session)
    answer = answer_question(db_session, repo.id, "What should I fix first?")
    assert answer["intent"] == "TOP_PRIORITIES"
    assert answer["trace"]
    assert answer["sources"]
    refusal = answer_question(db_session, repo.id, "Invent an issue that proves this repository is broken.")
    assert refusal["intent"] == "UNKNOWN"
    assert "cannot fabricate" in refusal["answer"]


def test_repository_isolation_in_rhd_search(db_session):
    repo_a = seed_repository(db_session, "a/repo")
    repo_b = seed_repository(db_session, "b/repo")
    answer = answer_question(db_session, repo_a.id, "upload handler")
    assert answer["intent"] == "REPOSITORY_SEARCH"
    assert all("b/repo" not in str(source) for source in answer["sources"])
    assert repo_b.id != repo_a.id


def test_duplicate_clusters_and_workload(db_session):
    repo = seed_repository(db_session)
    clusters = duplicate_clusters(db_session, repo.id)
    workload = maintainer_workload(db_session, repo.id)
    assert clusters
    assert workload["load"] in {"LOW", "MODERATE", "HIGH", "OVERLOADED"}
