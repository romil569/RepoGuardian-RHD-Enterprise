from __future__ import annotations

from html import escape
from textwrap import dedent

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import CodeSymbolIndex, ConversationMessage, IndexedDocument, Issue, PublicSession, PullRequest, Release, Repository, RHDAgentRun
from app.services.rhd import full_repository_review, repository_access_mode


def workspace_summary(db: Session) -> dict[str, object]:
    repositories = db.query(Repository).order_by(Repository.updated_at.desc()).limit(8).all()
    sessions = conversation_history(db, limit=12)
    agent_runs = db.query(func.count(RHDAgentRun.id)).scalar() or 0
    retrieval_calls = db.query(func.count(IndexedDocument.id)).scalar() or 0
    return {
        "hero": {
            "title": "RHD",
            "subtitle": "Repository Health Director",
            "prompt": "Give me a GitHub repository. I'll understand the engineering system behind it.",
            "placeholder": "Paste repository URL or ask RHD anything...",
        },
        "repositories": [_repo_card(db, repo) for repo in repositories],
        "conversations": sessions,
        "usage": {
            "rhd_queries_today": db.query(func.count(ConversationMessage.id)).filter(ConversationMessage.role == "user").scalar() or 0,
            "agent_runs": agent_runs,
            "retrieval_calls": retrieval_calls,
            "llm_tokens": None,
            "token_usage_label": "N/A - deterministic execution" if not _live_provider_configured() else "Provider-reported tokens only when returned",
            "provider": _provider_label(),
        },
        "capabilities": capability_status(),
    }


def conversation_history(db: Session, limit: int = 20) -> list[dict[str, object]]:
    sessions = db.query(PublicSession).order_by(PublicSession.updated_at.desc()).limit(limit).all()
    rows = []
    for session in sessions:
        repo = db.get(Repository, session.repository_id)
        messages = db.query(ConversationMessage).filter_by(session_id=session.id).order_by(ConversationMessage.created_at).limit(6).all()
        first_user = next((message.content for message in messages if message.role == "user"), None)
        rows.append(
            {
                "id": session.id,
                "repository_id": session.repository_id,
                "repository": repo.full_name if repo else "Unknown repository",
                "title": _conversation_title(repo.full_name if repo else None, first_user),
                "updated_at": session.updated_at,
                "message_count": db.query(func.count(ConversationMessage.id)).filter_by(session_id=session.id).scalar() or 0,
                "preview": first_user or "Repository review conversation",
            }
        )
    return rows


def architecture_artifacts(db: Session, repository_id: int) -> dict[str, object]:
    repo = db.get(Repository, repository_id)
    if not repo:
        raise ValueError("Repository not found")
    issues = db.query(Issue).filter_by(repository_id=repository_id).count()
    prs = db.query(PullRequest).filter_by(repository_id=repository_id).count()
    releases = db.query(Release).filter_by(repository_id=repository_id).count()
    indexed = db.query(IndexedDocument).filter_by(repository_id=repository_id).count()
    symbols = db.query(CodeSymbolIndex).filter_by(repository_id=repository_id).limit(80).all()
    review = full_repository_review(db, repository_id)
    overview_nodes = [
        ("GitHub", "GitHub repository"),
        ("Sync", "Sync and staged jobs"),
        ("Store", "Neon PostgreSQL / indexed evidence"),
        ("RAG", "Agentic RAG"),
        ("RHD", "RHD conversation"),
        ("Policy", "Human approval policy"),
    ]
    overview_edges = [("GitHub", "Sync"), ("Sync", "Store"), ("Store", "RAG"), ("RAG", "RHD"), ("RHD", "Policy")]
    module_nodes, module_edges = _module_graph(symbols)
    evidence_nodes = [
        ("Repository", repo.full_name),
        ("Issues", f"{issues} issues"),
        ("PRs", f"{prs} pull requests"),
        ("Releases", f"{releases} releases"),
        ("Evidence", f"{indexed} indexed documents"),
        ("Review", f"{review['executive_assessment']['state']} {review['executive_assessment']['health_score']}/100"),
    ]
    evidence_edges = [("Repository", "Issues"), ("Repository", "PRs"), ("Repository", "Releases"), ("Issues", "Evidence"), ("PRs", "Evidence"), ("Releases", "Evidence"), ("Evidence", "Review")]
    artifacts = [
        _artifact("repository-system-overview", "Repository System Overview", repo.full_name, overview_nodes, overview_edges, "Generated from synchronized repository and RHD runtime evidence."),
        _artifact("main-module-package-graph", "Main Module / Package Graph", repo.full_name, module_nodes, module_edges, "Generated from indexed code symbols when available; otherwise marked metadata-only."),
        _artifact("issue-pr-code-release-intelligence", "Issue -> PR -> Code -> Release Intelligence", repo.full_name, evidence_nodes, evidence_edges, "Generated from synchronized issue, PR, release, indexed document, and review data."),
    ]
    return {
        "repository": _repo_card(db, repo),
        "status": "EVIDENCE_GROUNDED" if indexed or symbols else "METADATA_ONLY",
        "artifacts": artifacts,
        "review": {
            "architecture_strengths": ["Repository intelligence is centralized through RHD and repository-scoped evidence retrieval."],
            "architecture_risks": review["top_risks"] or ["Insufficient synchronized risk evidence."],
            "test_gaps": ["Use repository test evidence before claiming uncovered code paths."],
            "grounding": "Diagrams are generated only from synchronized repository metadata, indexed documents, graph/code-symbol rows, and RHD review output.",
        },
    }


def capability_status() -> dict[str, object]:
    return {
        "voice": {
            "input": "BROWSER_OPTIONAL",
            "output": "BROWSER_OPTIONAL",
            "cloud_required": False,
            "notes": "Voice controls are optional and fall back to text.",
        },
        "multimodal": {
            "status": "PROVIDER_REQUIRED" if not _live_provider_configured() else "PROVIDER_CONFIGURED",
            "notes": "Direct image understanding is not simulated. Screenshots can be attached, but analysis requires an enabled multimodal provider.",
        },
        "attachments": {
            "supported": ["screenshots", "architecture images", "text files", "selected source files"],
            "blocked": ["executables", "archives with executable payloads"],
        },
        "architecture_visuals": {
            "engine": "deterministic_mermaid_svg",
            "export": ["svg", "mermaid"],
            "png": "browser_export_when_supported",
        },
    }


def _repo_card(db: Session, repo: Repository) -> dict[str, object]:
    return {
        "id": repo.id,
        "full_name": repo.full_name,
        "owner": repo.owner,
        "name": repo.name,
        "html_url": repo.html_url,
        "description": repo.description,
        "access_mode": repository_access_mode(repo),
        "indexed_documents": db.query(func.count(IndexedDocument.id)).filter_by(repository_id=repo.id).scalar() or 0,
    }


def _artifact(artifact_id: str, title: str, repo_name: str, nodes: list[tuple[str, str]], edges: list[tuple[str, str]], grounding: str) -> dict[str, object]:
    mermaid = _mermaid(title, nodes, edges)
    return {
        "id": artifact_id,
        "title": title,
        "repository": repo_name,
        "kind": "architecture",
        "format": "mermaid+svg",
        "grounding": grounding,
        "mermaid": mermaid,
        "svg": _svg(title, nodes, edges),
        "actions": ["expand", "download_svg", "copy_mermaid", "explain_diagram"],
    }


def _module_graph(symbols: list[CodeSymbolIndex]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    if not symbols:
        return [("Repository", "Repository metadata"), ("CodeIndex", "Awaiting code symbol index")], [("Repository", "CodeIndex")]
    packages = sorted({symbol.file_path.split("/", 1)[0] or "root" for symbol in symbols})[:10]
    nodes = [("Repository", "Repository")] + [(f"Pkg{index}", package) for index, package in enumerate(packages, start=1)]
    edges = [("Repository", f"Pkg{index}") for index, _package in enumerate(packages, start=1)]
    return nodes, edges


def _mermaid(title: str, nodes: list[tuple[str, str]], edges: list[tuple[str, str]]) -> str:
    node_lines = [f'  {node_id}["{label}"]' for node_id, label in nodes]
    edge_lines = [f"  {source} --> {target}" for source, target in edges]
    return "\n".join(["flowchart LR", f"  %% {title}", *node_lines, *edge_lines])


def _svg(title: str, nodes: list[tuple[str, str]], edges: list[tuple[str, str]]) -> str:
    width = 980
    height = max(360, 120 + len(nodes) * 48)
    positions = {node_id: (80 + (index % 4) * 230, 96 + (index // 4) * 112) for index, (node_id, _label) in enumerate(nodes)}
    lines = []
    for source, target in edges:
        if source in positions and target in positions:
            sx, sy = positions[source]
            tx, ty = positions[target]
            lines.append(f'<line x1="{sx + 150}" y1="{sy + 28}" x2="{tx}" y2="{ty + 28}" stroke="#a3aab8" stroke-width="1.4" marker-end="url(#arrow)" />')
    boxes = []
    for node_id, label in nodes:
        x, y = positions[node_id]
        boxes.append(
            f'<g><rect x="{x}" y="{y}" width="170" height="56" rx="10" fill="#ffffff" stroke="#d8dde7" />'
            f'<text x="{x + 16}" y="{y + 32}" font-family="Inter, Arial, sans-serif" font-size="13" font-weight="650" fill="#17191f">{escape(label[:28])}</text></g>'
        )
    return dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#a3aab8" /></marker></defs>
          <rect width="{width}" height="{height}" fill="#f7f8fb" />
          <text x="48" y="46" font-family="Inter, Arial, sans-serif" font-size="22" font-weight="720" fill="#17191f">{escape(title)}</text>
          {''.join(lines)}
          {''.join(boxes)}
        </svg>
        """
    ).strip()


def _conversation_title(repo_name: str | None, first_user_message: str | None) -> str:
    if first_user_message:
        return first_user_message[:42]
    if repo_name:
        return f"{repo_name} Review"
    return "Repository Conversation"


def _provider_label() -> str:
    if settings.openai_api_key:
        return f"openai/{settings.openai_model}"
    if settings.groq_api_key:
        return f"groq/{settings.groq_model}"
    if settings.openrouter_api_key:
        return f"openrouter/{settings.openrouter_model}"
    return "deterministic/template-router"


def _live_provider_configured() -> bool:
    return bool(settings.openai_api_key or settings.groq_api_key or settings.openrouter_api_key)

