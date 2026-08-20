from __future__ import annotations

from app.api.routes.workspace_v5 import rhd_v5_architecture, rhd_v5_capabilities, rhd_v5_conversations, rhd_v5_workspace
from app.db.models import CodeSymbolIndex, ConversationMessage, PublicSession, Repository


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
    assert len(result["artifacts"]) == 3
    assert all("mermaid" in artifact and "svg" in artifact for artifact in result["artifacts"])
    assert "backend" in result["artifacts"][1]["svg"]


def test_v5_conversations_are_repository_scoped(db_session):
    repo = add_repo(db_session)
    session = PublicSession(id="session-2", repository_id=repo.id, metadata_json={})
    db_session.add(session)
    db_session.add(ConversationMessage(session_id=session.id, repository_id=repo.id, role="user", content="Find risky code"))
    db_session.commit()

    result = rhd_v5_conversations(10, db_session)

    assert result["conversations"][0]["repository"] == repo.full_name
    assert result["conversations"][0]["preview"] == "Find risky code"
