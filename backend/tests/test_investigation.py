from __future__ import annotations

from app.agents.tools.analysis import ALLOWED_CLASSIFICATIONS, ALLOWED_ESCALATIONS, ALLOWED_PRIORITIES
from app.agents.workflows.investigation import InvestigationOrchestrator
from app.db.models import IndexedDocument, Issue, PullRequest, Release, Repository
from app.services.text import vectorize


def test_investigation_schema_and_allowed_values(db_session):
    repo = Repository(github_id=1, owner="owner", name="demo", full_name="owner/demo", html_url="https://github.com/owner/demo")
    db_session.add(repo)
    db_session.flush()
    issue = Issue(
        repository_id=repo.id,
        github_id=11,
        github_issue_number=1,
        title="Application is not working",
        body="Please fix.",
        state="OPEN",
        labels=["needs-info"],
        html_url="https://github.com/owner/demo/issues/1",
    )
    related = Issue(
        repository_id=repo.id,
        github_id=12,
        github_issue_number=2,
        title="Login fails after latest update",
        body="Steps: login. Expected dashboard. Actual error. Environment Windows. Version v1.2.0.",
        state="OPEN",
        labels=["bug"],
        html_url="https://github.com/owner/demo/issues/2",
    )
    pr = PullRequest(repository_id=repo.id, github_id=20, github_pr_number=3, title="Refactor login validation", body="auth validation", state="OPEN", html_url="https://github.com/owner/demo/pull/3")
    release = Release(repository_id=repo.id, github_id=30, tag="v1.2.0", name="v1.2.0", body="auth changes", html_url="https://github.com/owner/demo/releases/tag/v1.2.0")
    db_session.add_all([issue, related, pr, release])
    db_session.flush()
    for item in [issue, related]:
        db_session.add(
            IndexedDocument(
                repository_id=repo.id,
                source_type="ISSUE",
                source_id=item.id,
                github_number=item.github_issue_number,
                title=item.title,
                source_url=item.html_url,
                text=item.body or "",
                token_vector=vectorize(f"{item.title}\n{item.body or ''}"),
            )
        )
    db_session.commit()

    result = InvestigationOrchestrator(db_session).investigate_issue(issue.id)
    assert result["classification"]["category"] in ALLOWED_CLASSIFICATIONS
    assert result["priority"]["level"] in ALLOWED_PRIORITIES
    assert result["escalation"]["decision"] in ALLOWED_ESCALATIONS
    assert result["escalation"]["decision"] == "NEEDS_INFORMATION"
    assert "investigation_trace" in result
    assert all(0.0 <= float(result[key]["confidence"]) <= 1.0 for key in ["classification", "priority", "escalation"])
