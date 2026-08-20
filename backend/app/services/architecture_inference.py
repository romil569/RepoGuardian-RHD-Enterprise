from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from textwrap import dedent
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ArchitectureArtifact, CodeSymbolIndex, IndexedDocument, Repository
from app.github.client import GitHubCliService, GitHubRestService, github_service
from app.services.code_intelligence import detect_language, extract_python_symbols, extract_regex_symbols

SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".cpp", ".c", ".h"}
MANIFESTS = {"package.json", "requirements.txt", "pyproject.toml", "Dockerfile", "docker-compose.yml", "vercel.json", "next.config.ts", "alembic.ini", ".github/workflows"}


def analyze_repository_source(db: Session, repository_id: int, github: GitHubCliService | GitHubRestService | None = None) -> dict[str, Any]:
    repo = _repo(db, repository_id)
    github = github or github_service()
    tree = github.get_repository_tree(repo.full_name, repo.default_branch, limit=settings.max_initial_code_files)
    files = [item for item in tree if item.get("type") == "blob"]
    selected = _select_files(files)
    symbols_written = 0
    code_documents = 0
    languages: set[str] = set()
    components = _infer_components_from_paths(files)
    for item in selected:
        path = str(item.get("path") or "")
        try:
            text = github.get_file_text(repo.full_name, path, repo.default_branch)
        except Exception:
            continue
        if not text:
            continue
        language = detect_language(Path(path)) or _language_from_manifest(path)
        if language:
            languages.add(language)
        if detect_language(Path(path)):
            extracted = extract_python_symbols(repository_id, path, text) if language == "Python" else extract_regex_symbols(repository_id, path, language or "Text", text)
            symbols_written += _persist_symbols(db, extracted)
        _upsert_code_document(db, repository_id, path, text, item, language)
        code_documents += 1
    db.commit()
    return {
        "tree_files_seen": len(files),
        "files_analyzed": code_documents,
        "symbols_indexed": symbols_written,
        "languages": sorted(languages),
        "components": components,
        "bounded": len(files) >= settings.max_initial_code_files,
        "default_branch": repo.default_branch,
    }


def generate_architecture_artifacts(db: Session, repository_id: int, conversation_id: str | None = None) -> dict[str, Any]:
    repo = _repo(db, repository_id)
    symbols = db.query(CodeSymbolIndex).filter_by(repository_id=repository_id).limit(160).all()
    docs = db.query(IndexedDocument).filter_by(repository_id=repository_id, source_type="code").limit(160).all()
    components = _components_from_evidence(symbols, docs)
    evidence_version = _evidence_version(repo, docs, symbols)
    artifacts = [
        _artifact(repo, conversation_id, "SYSTEM", "System Architecture", _system_nodes(repo, components), _system_edges(components), evidence_version),
        _artifact(repo, conversation_id, "MODULES", "Module Dependency Graph", _module_nodes(components), _module_edges(components), evidence_version),
    ]
    if any("Data" in labels for labels in components.values()):
        artifacts.append(_artifact(repo, conversation_id, "DATA_FLOW", "Data Flow", _data_nodes(repo, components), _data_edges(components), evidence_version))
    persisted = [_persist_artifact(db, artifact) for artifact in artifacts]
    db.commit()
    return {
        "status": "EVIDENCE_GROUNDED" if docs or symbols else "INSUFFICIENT_CODE_EVIDENCE",
        "repository_id": repository_id,
        "commit_sha": None,
        "evidence_version": evidence_version,
        "artifacts": persisted,
    }


def architecture_payload(db: Session, repository_id: int) -> dict[str, Any]:
    repo = _repo(db, repository_id)
    rows = db.query(ArchitectureArtifact).filter_by(repository_id=repository_id).order_by(ArchitectureArtifact.generated_at.desc()).all()
    latest_rows: list[ArchitectureArtifact] = []
    seen_types: set[str] = set()
    for row in rows:
        if row.artifact_type in seen_types:
            continue
        seen_types.add(row.artifact_type)
        latest_rows.append(row)
    return {
        "repository": {"id": repo.id, "full_name": repo.full_name, "last_synced_at": repo.last_synced_at},
        "status": "EVIDENCE_GROUNDED" if latest_rows else "NO_ARCHITECTURE_ARTIFACT",
        "artifacts": [_artifact_row(row) for row in latest_rows],
    }


def _repo(db: Session, repository_id: int) -> Repository:
    repo = db.get(Repository, repository_id)
    if not repo:
        raise ValueError("Repository not found")
    return repo


def _select_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = []
    for item in files:
        path = str(item.get("path") or "")
        size = int(item.get("size") or 0)
        if size > settings.max_code_file_bytes:
            continue
        if Path(path).suffix.lower() in SOURCE_EXTENSIONS or any(path.endswith(manifest) or manifest in path for manifest in MANIFESTS):
            selected.append(item)
        if len(selected) >= min(settings.max_initial_code_files, 80):
            break
    return selected


def _persist_symbols(db: Session, symbols: list[Any]) -> int:
    written = 0
    for symbol in symbols:
        existing = db.query(CodeSymbolIndex).filter_by(repository_id=symbol.repository_id, file_path=symbol.file_path, symbol_name=symbol.symbol_name, start_line=symbol.start_line).one_or_none()
        if existing:
            existing.end_line = symbol.end_line
            existing.language = symbol.language
            existing.symbol_type = symbol.symbol_type
        else:
            db.add(CodeSymbolIndex(**symbol.__dict__))
            written += 1
    return written


def _upsert_code_document(db: Session, repository_id: int, path: str, text: str, item: dict[str, Any], language: str | None) -> None:
    source_id = _source_id_for_path(path)
    existing = db.query(IndexedDocument).filter_by(repository_id=repository_id, source_type="code", source_id=source_id).one_or_none()
    doc = existing or IndexedDocument(repository_id=repository_id, source_type="code", source_id=source_id, title=path, text="")
    doc.github_number = None
    doc.title = path
    doc.text = text[:12000]
    doc.source_url = None
    doc.token_vector = {"size": float(item.get("size") or len(text)), "language": float(len(language or ""))}
    doc.updated_at = datetime.now(UTC)
    if not existing:
        db.add(doc)


def _source_id_for_path(path: str) -> int:
    return int(hashlib.sha256(path.encode("utf-8")).hexdigest()[:8], 16) % 2_147_483_647


def _language_from_manifest(path: str) -> str | None:
    if path.endswith("package.json"):
        return "Node"
    if path.endswith(("requirements.txt", "pyproject.toml")):
        return "Python"
    if path.endswith("Dockerfile"):
        return "Docker"
    return None


def _infer_components_from_paths(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = [str(item.get("path") or "") for item in files]
    return [{"path": path, "layer": _layer_for_path(path), "type": "file"} for path in paths[:200]]


def _components_from_evidence(symbols: list[CodeSymbolIndex], docs: list[IndexedDocument]) -> dict[str, list[str]]:
    components: dict[str, list[str]] = {}
    for doc in docs:
        component = _component_for_path(doc.title)
        labels = components.setdefault(component, [])
        layer = _layer_for_path(doc.title)
        if layer not in labels:
            labels.append(layer)
    for symbol in symbols:
        component = _component_for_path(symbol.file_path)
        labels = components.setdefault(component, [])
        if "Code" not in labels:
            labels.append("Code")
    return components or {"Repository Metadata": ["Repository"]}


def _component_for_path(path: str) -> str:
    lower = path.lower()
    if lower.startswith(("frontend/", "app/", "pages/", "components/")) or lower.endswith((".tsx", ".jsx")):
        return "Frontend"
    if "api" in lower or "routes" in lower:
        return "API"
    if "service" in lower or "services" in lower:
        return "Domain Services"
    if "model" in lower or "schema" in lower or "db" in lower or "database" in lower:
        return "Data Access"
    if "test" in lower or "spec" in lower:
        return "Tests"
    if ".github/workflows" in lower or "docker" in lower or "vercel" in lower:
        return "CI/CD"
    if "rag" in lower or "ml" in lower or "agent" in lower:
        return "AI/ML"
    return Path(path).parts[0].title() if Path(path).parts else "Repository"


def _layer_for_path(path: str) -> str:
    component = _component_for_path(path)
    return {
        "Frontend": "Frontend",
        "API": "API",
        "Domain Services": "Backend",
        "Data Access": "Data",
        "Tests": "Tests",
        "CI/CD": "CI/CD",
        "AI/ML": "AI/ML",
    }.get(component, "Code")


def _system_nodes(repo: Repository, components: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    nodes = [("User", "User", "External"), ("Repo", repo.full_name, "Repository")]
    nodes.extend((_safe_id(name), name, labels[0]) for name, labels in components.items())
    return nodes


def _system_edges(components: dict[str, list[str]]) -> list[tuple[str, str]]:
    edges = [("User", "Repo")]
    order = ["Frontend", "API", "Domain Services", "Data Access", "AI/ML", "CI/CD", "Tests"]
    present = [_safe_id(name) for name in order if name in components]
    if present:
        edges.append(("Repo", present[0]))
        edges.extend((present[index], present[index + 1]) for index in range(len(present) - 1))
    else:
        edges.extend(("Repo", _safe_id(name)) for name in components)
    return edges


def _module_nodes(components: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    return [(_safe_id(name), name, ",".join(labels)) for name, labels in components.items()]


def _module_edges(components: dict[str, list[str]]) -> list[tuple[str, str]]:
    names = list(components)
    return [(_safe_id(names[index]), _safe_id(names[index + 1])) for index in range(max(0, len(names) - 1))]


def _data_nodes(repo: Repository, components: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    nodes = [("Repo", repo.full_name, "Repository")]
    for name, labels in components.items():
        if any(label in {"API", "Backend", "Data", "AI/ML"} for label in labels):
            nodes.append((_safe_id(name), name, ",".join(labels)))
    return nodes


def _data_edges(components: dict[str, list[str]]) -> list[tuple[str, str]]:
    ordered = [_safe_id(name) for name, labels in components.items() if any(label in {"API", "Backend", "Data", "AI/ML"} for label in labels)]
    return [("Repo", ordered[0])] + [(ordered[index], ordered[index + 1]) for index in range(len(ordered) - 1)] if ordered else []


def _artifact(repo: Repository, conversation_id: str | None, artifact_type: str, title: str, nodes: list[tuple[str, str, str]], edges: list[tuple[str, str]], evidence_version: str) -> dict[str, Any]:
    mermaid = _mermaid(title, nodes, edges)
    return {
        "id": str(uuid.uuid4()),
        "repository_id": repo.id,
        "conversation_id": conversation_id,
        "commit_sha": None,
        "artifact_type": artifact_type,
        "title": title,
        "diagram_source": mermaid,
        "svg": _svg(title, nodes, edges),
        "metadata_json": {"nodes": [{"id": node_id, "label": label, "type": node_type, "confidence": "MEDIUM"} for node_id, label, node_type in nodes], "edges": [{"source": source, "target": target, "confidence": "MEDIUM"} for source, target in edges]},
        "evidence_version": evidence_version,
    }


def _persist_artifact(db: Session, artifact: dict[str, Any]) -> dict[str, Any]:
    existing = db.query(ArchitectureArtifact).filter_by(repository_id=artifact["repository_id"], artifact_type=artifact["artifact_type"], evidence_version=artifact["evidence_version"]).one_or_none()
    row = existing or ArchitectureArtifact(id=artifact["id"], repository_id=artifact["repository_id"], artifact_type=artifact["artifact_type"], evidence_version=artifact["evidence_version"], title=artifact["title"], diagram_source="", svg="")
    row.conversation_id = artifact["conversation_id"]
    row.commit_sha = artifact["commit_sha"]
    row.title = artifact["title"]
    row.diagram_source = artifact["diagram_source"]
    row.svg = artifact["svg"]
    row.metadata_json = artifact["metadata_json"]
    row.generated_at = datetime.now(UTC)
    if not existing:
        db.add(row)
    return _artifact_row(row)


def _artifact_row(row: ArchitectureArtifact) -> dict[str, Any]:
    return {
        "id": row.id,
        "repository_id": row.repository_id,
        "conversation_id": row.conversation_id,
        "commit_sha": row.commit_sha,
        "artifact_type": row.artifact_type,
        "title": row.title,
        "mermaid": row.diagram_source,
        "diagram_source": row.diagram_source,
        "svg": row.svg,
        "metadata": row.metadata_json,
        "evidence_version": row.evidence_version,
        "generated_at": row.generated_at,
        "grounding": "Generated from synchronized repository tree, selected source files, code symbols, and indexed evidence.",
    }


def _evidence_version(repo: Repository, docs: list[IndexedDocument], symbols: list[CodeSymbolIndex]) -> str:
    base = f"{repo.full_name}:{repo.last_synced_at}:{len(docs)}:{len(symbols)}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _mermaid(title: str, nodes: list[tuple[str, str, str]], edges: list[tuple[str, str]]) -> str:
    lines = ["flowchart TD", f"  %% {title}"]
    for node_id, label, node_type in nodes:
        lines.append(f'  {node_id}["{label}<br/>{node_type}"]')
    lines.extend(f"  {source} --> {target}" for source, target in edges)
    return "\n".join(lines)


def _svg(title: str, nodes: list[tuple[str, str, str]], edges: list[tuple[str, str]]) -> str:
    width = 1080
    height = max(420, 150 + ((len(nodes) + 2) // 3) * 126)
    positions = {node_id: (64 + (index % 3) * 330, 98 + (index // 3) * 126) for index, (node_id, _label, _type) in enumerate(nodes)}
    lines = []
    for source, target in edges:
        if source in positions and target in positions:
            sx, sy = positions[source]
            tx, ty = positions[target]
            lines.append(f'<line x1="{sx + 240}" y1="{sy + 34}" x2="{tx}" y2="{ty + 34}" stroke="#aeb5c3" stroke-width="1.5" marker-end="url(#arrow)" />')
    boxes = []
    for node_id, label, node_type in nodes:
        x, y = positions[node_id]
        boxes.append(
            f'<g><rect x="{x}" y="{y}" width="250" height="72" rx="12" fill="#ffffff" stroke="#d8dde7" />'
            f'<text x="{x + 16}" y="{y + 30}" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="700" fill="#17191f">{escape(label[:34])}</text>'
            f'<text x="{x + 16}" y="{y + 52}" font-family="Inter, Arial, sans-serif" font-size="12" fill="#646b76">{escape(node_type)}</text></g>'
        )
    return dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#aeb5c3" /></marker></defs>
          <rect width="{width}" height="{height}" fill="#f7f8fb" />
          <text x="48" y="50" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="760" fill="#17191f">{escape(title)}</text>
          {''.join(lines)}
          {''.join(boxes)}
        </svg>
        """
    ).strip()


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "", value.title().replace(" ", "")) or "Node"
