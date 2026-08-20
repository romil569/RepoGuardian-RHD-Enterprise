from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine

from app.core.config import settings
from app.db.models import ConversationMessage, IndexedDocument, Issue, PullRequest, PublicSession, Release, Repository
from app.platform.deployment import database_runtime_checks, deployment_profile, queue_runtime_check
from app.platform.queue import JobStatus, JobType, LocalJobQueue, PostgresJobQueue, create_job_queue
from app.services.rate_limit import check_rate_limit
from app.services.sessions import ensure_public_session, record_message
from app.platform.tool_registry import execute_tool, list_tools
from app.rag.agentic import evaluate_retrieval, plan_query, retrieve_agentic_evidence


def _repo(db_session) -> Repository:
    repo = Repository(github_id=9001, owner="owner", name="enterprise", full_name="owner/enterprise", html_url="https://github.com/owner/enterprise")
    db_session.add(repo)
    db_session.flush()
    return repo


def test_deployment_profile_lists_managed_cloud_mode():
    profile = deployment_profile()
    assert "MANAGED_CLOUD" in profile["supported_modes"]
    assert profile["managed_cloud"]["backend"] == "Vercel Python serverless FastAPI"
    assert profile["managed_cloud"]["queue"] == "Postgres serverless job queue, local development fallback"


def test_database_runtime_checks_report_sqlite_as_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "database_url", "sqlite:///local.db")
    engine = create_engine("sqlite:///:memory:")
    rows = database_runtime_checks(engine)
    assert rows[0].component == "postgres"
    assert rows[0].status == "NOT_CONFIGURED"


def test_queue_selector_defaults_to_local_without_managed_services(monkeypatch):
    monkeypatch.setattr(settings, "queue_backend", "redis")
    monkeypatch.setattr(settings, "redis_url", None)
    assert isinstance(create_job_queue(), LocalJobQueue)
    check = queue_runtime_check()
    assert check.component == "queue"


def test_agentic_rag_plans_release_and_pr_context():
    plan = plan_query("What broke after v1.2.0 in the auth PR?")
    strategies = {item.value for item in plan.strategies}
    assert {"BM25", "DENSE", "RELEASE", "PR", "RECENT"}.issubset(strategies)


def test_agentic_rag_retrieves_repository_scoped_hybrid_evidence(db_session):
    repo = _repo(db_session)
    issue = Issue(
        repository_id=repo.id,
        github_id=1,
        github_issue_number=1,
        title="Login fails after v1.2.0",
        body="Authentication fails after release v1.2.0 on Windows.",
        state="OPEN",
        labels=["bug"],
        html_url="https://github.com/owner/enterprise/issues/1",
        updated_at=datetime.now(UTC),
    )
    pr = PullRequest(
        repository_id=repo.id,
        github_id=2,
        github_pr_number=2,
        title="Refactor authentication middleware",
        body="Touches login validation.",
        state="OPEN",
        html_url="https://github.com/owner/enterprise/pull/2",
        updated_at=datetime.now(UTC),
    )
    release = Release(repository_id=repo.id, github_id=3, tag="v1.2.0", body="Auth validation changes.", html_url="https://github.com/owner/enterprise/releases/tag/v1.2.0", published_at=datetime.now(UTC))
    db_session.add_all([issue, pr, release])
    db_session.flush()
    db_session.add(IndexedDocument(repository_id=repo.id, source_type="issue", source_id=issue.id, github_number=1, title=issue.title, source_url=issue.html_url, text=issue.body or "", token_vector={"auth": 1.0, "release": 1.0}))
    db_session.commit()

    result = retrieve_agentic_evidence(db_session, repo.id, "What broke after v1.2.0 auth release?", top_k=5)

    assert result["critic"]["status"] == "PASSED"
    assert result["evidence"]
    assert all(item["repository_id"] == repo.id for item in result["evidence"])


def test_retrieval_evaluation_uses_objective_metrics():
    metrics = evaluate_retrieval(["issue:1", "pr:2", "issue:3"], {"pr:2", "release:1"}, k=3)
    assert metrics["recall_at_k"] == 0.5
    assert metrics["mrr"] == 0.5
    assert 0 < metrics["ndcg"] < 1


def test_tool_registry_lists_safety_and_gates_write_tools(db_session):
    tools = {item["name"]: item for item in list_tools()}
    assert tools["rhd_search_repository"]["safety"] == "read"
    assert tools["rhd_prepare_action"]["requires_approval"] is True

    response = execute_tool(db_session, "rhd_prepare_action", {"repository_id": 1, "action_type": "POST_COMMENT"})
    assert response["status"] == "APPROVAL_REQUIRED"


def test_public_session_persists_repository_scoped_messages(db_session):
    repo = _repo(db_session)
    session = ensure_public_session(db_session, repo.id)
    record_message(db_session, session.id, repo.id, "user", "What should I fix first?")
    db_session.commit()

    assert db_session.get(PublicSession, session.id).repository_id == repo.id
    assert db_session.query(ConversationMessage).filter_by(session_id=session.id, repository_id=repo.id).count() == 1
    assert ensure_public_session(db_session, repo.id, session.id).id == session.id


def test_rate_limit_uses_local_fallback_when_postgres_disabled(monkeypatch):
    monkeypatch.setattr(settings, "queue_backend", "local")
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    assert check_rate_limit("test-client:expensive", "expensive", 1) is True
    assert check_rate_limit("test-client:expensive", "expensive", 1) is False


def test_postgres_job_queue_class_round_trips_with_monkeypatched_session(db_session, monkeypatch):
    import app.platform.queue as queue_module

    class SessionFactory:
        def __call__(self):
            return db_session

    monkeypatch.setattr(queue_module, "SessionLocal", SessionFactory())
    queue = PostgresJobQueue()
    job = queue.enqueue(JobType.INITIAL_RHD_REVIEW, 1, {"stage": "CONNECT"}, correlation_id="job-1")
    duplicate = queue.enqueue(JobType.INITIAL_RHD_REVIEW, 1, {"stage": "CONNECT"}, correlation_id="job-1")

    assert duplicate.id == job.id
    assert queue.get(job.id).status == JobStatus.QUEUED
