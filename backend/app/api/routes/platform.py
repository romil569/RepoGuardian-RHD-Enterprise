from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Repository
from app.db.session import get_db
from app.ml.registry import model_status_cards
from app.platform.model_gateway import ModelGateway, ModelRequest
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


@router.post("/code/analyze")
def code_analyze(request: CodeAnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if not db.get(Repository, request.repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    path = Path(request.local_path).resolve()
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=422, detail="Local source path must be an existing directory")
    analysis = analyze_source_tree(request.repository_id, path)
    graph = build_code_graph(request.repository_id, analysis)
    return {
        "analysis": analysis,
        "graph": {"nodes": len(graph.nodes), "edges": len(graph.edges)},
        "root_cause_hypotheses": root_cause_hypotheses(request.issue_text or "", analysis),
    }
