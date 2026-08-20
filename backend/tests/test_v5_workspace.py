from __future__ import annotations

import json

from app.api.routes.workspace_v5 import RepositoryAnalyzeRequest, rhd_v5_analyze_repository, rhd_v5_architecture, rhd_v5_capabilities, rhd_v5_conversations, rhd_v5_job_status, rhd_v5_workspace
from app.db.models import ArchitectureArtifact, CodeSymbolIndex, ConversationMessage, DeploymentJob, PublicSession, Repository
from app.services.architecture_inference import _source_id_for_path
from app.services.serverless_jobs import _run_current_stage


def add_repo(db_session) -> Repository:
    repo = Repository(github_id=505, owner="owner", name="workspace", full_name="owner/workspace", html_url="https://github.com/owner/workspace")
    db_session.add(repo)
    db_session.flush()
    return repo


def test_v5_workspace_reports_truthful_usage_and_capabilities(db_session):
    repo = add_repo(db_session)
    session = PublicSession(id="session-1", repository_id=repo.id, metadata_json={})
    db_session.add(session)
    db_session.add(ConversationMessage(session_id=session.id, repository_id=repo.id, role="user", content="Review architecture"))
    db_session.commit()

    workspace = rhd_v5_workspace(db_session)
    capabilities = rhd_v5_capabilities()

    assert workspace["hero"]["title"] == "RHD"
    assert workspace["usage"]["token_usage_label"]
    assert workspace["conversations"][0]["title"] == "Review architecture"
    assert capabilities["multimodal"]["status"] in {"PROVIDER_REQUIRED", "PROVIDER_CONFIGURED"}
    assert "executables" in capabilities["attachments"]["blocked"]


def test_v5_architecture_artifacts_are_evidence_grounded_and_exportable(db_session):
    repo = add_repo(db_session)
    db_session.add(
        CodeSymbolIndex(
            repository_id=repo.id,
            file_path="backend/app/api/routes/workspace.py",
            language="Python",
            symbol_name="workspace",
            symbol_type="function",
            start_line=1,
            end_line=5,
        )
    )
    db_session.commit()

    result = rhd_v5_architecture(repo.id, db_session)

    assert result["status"] in {"EVIDENCE_GROUNDED", "METADATA_ONLY"}
    assert len(result["artifacts"]) >= 2
    assert all("mermaid" in artifact and "svg" in artifact for artifact in result["artifacts"])
    assert "API" in result["artifacts"][0]["svg"] or "API" in result["artifacts"][1]["svg"]
    assert db_session.query(ArchitectureArtifact).filter_by(repository_id=repo.id).count() >= 1


def test_v5_conversations_are_repository_scoped(db_session):
    repo = add_repo(db_session)
    session = PublicSession(id="session-2", repository_id=repo.id, metadata_json={})
    db_session.add(session)
    db_session.add(ConversationMessage(session_id=session.id, repository_id=repo.id, role="user", content="Find risky code"))
    db_session.commit()

    result = rhd_v5_conversations(10, db_session)

    assert result["conversations"][0]["repository"] == repo.full_name
    assert result["conversations"][0]["preview"] == "Find risky code"


def test_v51_analysis_start_and_job_status_contract(db_session, monkeypatch):
    def fake_connect_repository(db, full_name):
        repo = Repository(github_id=808, owner=full_name.split("/")[0], name=full_name.split("/")[1], full_name=full_name, html_url=f"https://github.com/{full_name}")
        db.add(repo)
        db.flush()
        return repo, True

    monkeypatch.setattr("app.services.repository_analysis_orchestrator.connect_repository", fake_connect_repository)

    started = rhd_v5_analyze_repository(RepositoryAnalyzeRequest(repository="github.com/owner/contract"), db_session)
    status = rhd_v5_job_status(started["job_id"], db_session)

    assert started["status"] == "QUEUED"
    assert started["repository_id"]
    assert status["job_id"] == started["job_id"]
    assert status["current_stage"] in {"SYNC_METADATA", "CONNECT"}
    assert status["repository"]["full_name"] == "owner/contract"


def test_v51_architecture_isolation_between_repositories(db_session):
    repo_a = add_repo(db_session)
    repo_b = Repository(github_id=606, owner="other", name="repo", full_name="other/repo", html_url="https://github.com/other/repo")
    db_session.add(repo_b)
    db_session.flush()
    db_session.add(CodeSymbolIndex(repository_id=repo_a.id, file_path="frontend/app/page.tsx", language="TypeScript", symbol_name="Page", symbol_type="function", start_line=1, end_line=3))
    db_session.add(CodeSymbolIndex(repository_id=repo_b.id, file_path="backend/app/main.py", language="Python", symbol_name="create_app", symbol_type="function", start_line=1, end_line=3))
    db_session.commit()

    arch_a = rhd_v5_architecture(repo_a.id, db_session)
    arch_b = rhd_v5_architecture(repo_b.id, db_session)

    assert arch_a["repository"]["full_name"] == repo_a.full_name
    assert arch_b["repository"]["full_name"] == repo_b.full_name
    assert "Frontend" in arch_a["artifacts"][0]["svg"]
    assert "API" in arch_b["artifacts"][0]["svg"] or "Backend" in arch_b["artifacts"][0]["svg"]


def test_v51_code_document_source_id_stays_inside_postgres_integer_range():
    source_id = _source_id_for_path("package.json")

    assert 0 <= source_id <= 2_147_483_646


def test_v51_architecture_stage_payload_is_json_serializable(db_session):
    repo = add_repo(db_session)
    db_session.add(CodeSymbolIndex(repository_id=repo.id, file_path="backend/app/main.py", language="Python", symbol_name="main", symbol_type="function", start_line=1, end_line=3))
    job = DeploymentJob(
        id="architecture-stage-json",
        repository_id=repo.id,
        job_type="v5_repository_analysis",
        payload={"repository": repo.full_name, "conversation_id": "session-json", "stage_results": {}},
        status="RUNNING",
        stage="GENERATE_ARCHITECTURE",
        progress=80,
        correlation_id="architecture-stage-json",
    )
    db_session.add(job)
    db_session.commit()

    _run_current_stage(db_session, job)

    json.dumps(job.payload)
    assert job.payload["stage_results"]["architecture"]["artifact_count"] >= 1
