from __future__ import annotations

from app.db.models import IndexedDocument, Issue, Repository
from app.rag.retriever import search_repository_history
from app.services.evidence import filter_valid_evidence
from app.services.github_sync import connect_repository, sync_repository


class FakeGitHub:
    def get_repository(self, full_name: str):
        owner, name = full_name.split("/")
        return {
            "id": f"repo-{full_name}",
            "owner": {"login": owner},
            "name": name,
            "nameWithOwner": full_name,
            "description": "Demo",
            "url": f"https://github.com/{full_name}",
            "defaultBranchRef": {"name": "main"},
            "primaryLanguage": {"name": "Python"},
            "stargazerCount": 1,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        }

    def get_repository_issues(self, full_name: str, state: str = "all", limit: int = 100):
        return [
            {
                "id": f"issue-{full_name}-1",
                "number": 1,
                "title": "Login fails after latest update",
                "body": "Steps: 1. Login. Expected dashboard. Actual error message after v1.2.0. Environment Windows.",
                "state": "OPEN",
                "author": {"login": "tester"},
                "labels": [{"name": "bug"}],
                "url": f"https://github.com/{full_name}/issues/1",
                "createdAt": "2026-01-03T00:00:00Z",
                "updatedAt": "2026-01-03T00:00:00Z",
                "closedAt": None,
            }
        ]

    def get_issue_comments(self, full_name: str, number: int):
        return [{"id": 10, "user": "maintainer", "body": "Looks related to auth validation.", "html_url": "https://example.test/comment", "created_at": "2026-01-03T00:00:00Z", "updated_at": "2026-01-03T00:00:00Z"}]

    def get_pull_requests(self, full_name: str, state: str = "all", limit: int = 100):
        return [
            {
                "id": f"pr-{full_name}-2",
                "number": 2,
                "title": "Refactor authentication middleware",
                "body": "Changes auth validation.",
                "state": "OPEN",
                "author": {"login": "dev"},
                "url": f"https://github.com/{full_name}/pull/2",
                "createdAt": "2026-01-04T00:00:00Z",
                "updatedAt": "2026-01-04T00:00:00Z",
                "mergedAt": None,
            }
        ]

    def get_releases(self, full_name: str, limit: int = 30):
        return [{"id": 3, "tagName": "v1.2.0", "name": "v1.2.0", "body": "Authentication validation changes.", "url": f"https://github.com/{full_name}/releases/tag/v1.2.0", "publishedAt": "2026-01-05T00:00:00Z"}]


def test_repository_sync_is_idempotent(db_session):
    repo, created = connect_repository(db_session, "owner/demo", FakeGitHub())
    assert created is True
    first = sync_repository(db_session, repo.id, FakeGitHub())
    second = sync_repository(db_session, repo.id, FakeGitHub())
    assert first["issues_added"] == 1
    assert second["issues_added"] == 0
    assert second["issues_updated"] == 1
    assert db_session.query(Issue).filter_by(repository_id=repo.id).count() == 1


def test_repository_specific_retrieval_isolation(db_session):
    repo_a = Repository(github_id=1, owner="a", name="repo", full_name="a/repo", html_url="https://example.test/a")
    repo_b = Repository(github_id=2, owner="b", name="repo", full_name="b/repo", html_url="https://example.test/b")
    db_session.add_all([repo_a, repo_b])
    db_session.flush()
    db_session.add_all(
        [
            IndexedDocument(repository_id=repo_a.id, source_type="ISSUE", source_id=1, github_number=1, title="Authentication bug", source_url="https://example.test/a/1", text="login auth failure", token_vector={"login": 1.0}),
            IndexedDocument(repository_id=repo_b.id, source_type="ISSUE", source_id=2, github_number=2, title="Other repository auth", source_url="https://example.test/b/2", text="login auth failure from repository b", token_vector={"login": 1.0}),
        ]
    )
    db_session.commit()
    results = search_repository_history(db_session, repo_a.id, "login")
    assert results
    assert all(result.repository_id == repo_a.id for result in results)
    assert all("repository b" not in result.snippet.lower() for result in results)


def test_fabricated_evidence_is_rejected(db_session):
    valid, rejected = filter_valid_evidence(
        db_session,
        [
            {
                "repository_id": 1,
                "source_type": "ISSUE",
                "source_id": 999999,
                "github_number": 999999,
                "title": "Fabricated",
                "source_url": "https://github.com/example/repo/issues/999999",
                "retrieval_score": 1.0,
                "why_relevant": "fake",
            }
        ],
    )
    assert valid == []
    assert len(rejected) == 1
