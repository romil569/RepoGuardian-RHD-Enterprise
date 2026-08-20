from __future__ import annotations

import json
from urllib.error import HTTPError

from fastapi.testclient import TestClient

from app.core.config import settings
from app.github import client as github_client
from app.github.client import GitHubAuthenticationError, GitHubRestService
from app.main import app


def test_readiness_endpoint_reports_application_status():
    response = TestClient(app).get("/readiness")
    assert response.status_code == 200
    assert response.json()["checks"]["application"] == "ok"


def test_public_mode_blocks_write_action_endpoints(monkeypatch):
    monkeypatch.setattr(settings, "public_analysis_mode", True)
    monkeypatch.setattr(settings, "enable_public_write_actions", False)
    response = TestClient(app).post("/api/action-recommendations/1/execute", json={"actor": "anonymous"})
    assert response.status_code == 403
    assert "read-only" in response.json()["detail"].lower()


def test_github_rest_service_maps_public_repository_response(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {
                    "id": 123,
                    "owner": {"login": "owner"},
                    "name": "repo",
                    "full_name": "owner/repo",
                    "description": "demo",
                    "html_url": "https://github.com/owner/repo",
                    "default_branch": "main",
                    "language": "Python",
                    "stargazers_count": 7,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ).encode("utf-8")

    monkeypatch.setattr(github_client, "urlopen", lambda request, timeout: FakeResponse())
    metadata = GitHubRestService().get_repository("owner/repo")
    assert metadata["nameWithOwner"] == "owner/repo"
    assert metadata["primaryLanguage"]["name"] == "Python"


def test_github_rest_service_hides_auth_details_on_rate_limit(monkeypatch):
    def blocked(_request, timeout):
        raise HTTPError("https://api.github.com/repos/owner/repo", 403, "rate limited", {}, None)

    monkeypatch.setattr(github_client, "urlopen", blocked)
    try:
        GitHubRestService().get_repository("owner/repo")
    except GitHubAuthenticationError as exc:
        assert "token" not in str(exc).lower()
    else:
        raise AssertionError("expected GitHubAuthenticationError")
