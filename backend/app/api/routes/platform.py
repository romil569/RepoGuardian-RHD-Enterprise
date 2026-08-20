from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Repository
from app.db.session import get_db
from app.ml.registry import model_status_cards
from app.platform.deployment import enterprise_readiness
from app.platform.model_gateway import ModelGateway, ModelRequest
from app.platform.tool_registry import execute_tool, list_tools
from app.rag.agentic import retrieve_agentic_evidence
from app.db.session import engine
from app.services.code_intelligence import analyze_source_tree, build_code_graph, root_cause_hypotheses

router = APIRouter(prefix="/api/platform", tags=["platform"])


class ModelProbeRequest(BaseModel):
    task: str = "intent"
    prompt: str = "status probe"
    repository_visibility: str = "public"


class CodeAnalyzeRequest(BaseModel):
    repository_id: int
    local_path: str
    issue_text: str | None = None


class RagQueryRequest(BaseModel):
    repository_id: int
    query: str
    top_k: int = 8


class ToolExecutionRequest(BaseModel):
    tool: str
    payload: dict[str, object] = {}
    approved: bool = False


@router.get("/model-gateway")
def model_gateway_status() -> dict[str, object]:
    gateway = ModelGateway.from_settings()
    return {"providers": gateway.status(), "priority": gateway.priority}


@router.post("/model-gateway/probe")
def model_gateway_probe(request: ModelProbeRequest) -> dict[str, object]:
    gateway = ModelGateway.from_settings()
    response = gateway.generate(ModelRequest(task=request.task, prompt=request.prompt, repository_visibility=request.repository_visibility))
    return response.__dict__


@router.get("/ml-models")
def ml_models() -> dict[str, object]:
    return {"models": [card.__dict__ | {"status": card.status.value} for card in model_status_cards()]}


@router.get("/enterprise-readiness")
def enterprise_readiness_status() -> dict[str, object]:
    return enterprise_readiness(engine)


@router.get("/tools")
def rhd_tools() -> dict[str, object]:
    return {"tools": list_tools()}


@router.post("/tools/execute")
def rhd_tool_execute(request: ToolExecutionRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return execute_tool(db, request.tool, request.payload, approved=request.approved)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/rag/query")
def rag_query(request: RagQueryRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if not db.get(Repository, request.repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    return retrieve_agentic_evidence(db, request.repository_id, request.query, request.top_k)


@router.post("/code/analyze")
def code_analyze(request: CodeAnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if not db.get(Repository, request.repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    path = Path(request.local_path).resolve()
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=422, detail="Local source path must be an existing directory")
    if not _code_path_allowed(path):
        raise HTTPException(status_code=403, detail="Local source path is outside configured code scan roots")
    analysis = analyze_source_tree(request.repository_id, path)
    graph = build_code_graph(request.repository_id, analysis)
    return {
        "analysis": analysis,
        "graph": {"nodes": len(graph.nodes), "edges": len(graph.edges)},
        "root_cause_hypotheses": root_cause_hypotheses(request.issue_text or "", analysis),
    }


def _code_path_allowed(path: Path) -> bool:
    configured = [item.strip() for item in settings.code_scan_allowed_roots.split(";") if item.strip()]
    roots = [Path(item).resolve() for item in configured] if configured else [Path.cwd().resolve().parent]
    return any(path == root or root in path.parents for root in roots)
