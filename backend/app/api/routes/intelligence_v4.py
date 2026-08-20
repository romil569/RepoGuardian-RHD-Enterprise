from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Repository
from app.db.session import get_db
from app.platform.agent_supervisor import agent_mesh_status, run_supervised_read_only_plan
from app.rag.agentic import describe_rag_pipeline, retrieve_agentic_evidence
from app.services.incident_intelligence import investigate_incident
from app.services.pr_intelligence import analyze_blast_radius, assess_pr_risk
from app.services.security_intelligence import prompt_injection_guard, redact_untrusted_text
from app.services.v4_observatory import mission_control, model_lab, neural_map, observatory

router = APIRouter(prefix="/api/v4", tags=["rhd-v4-intelligence"])


class IncidentRequest(BaseModel):
    repository_id: int
    query: str


class RagPipelineRequest(BaseModel):
    repository_id: int
    query: str = "What changed recently and what evidence supports it?"
    top_k: int = 8


class SecurityProbeRequest(BaseModel):
    text: str


class AgentRunRequest(BaseModel):
    repository_id: int | None = None
    objective: str = "Assess repository intelligence posture"


@router.get("/mission-control")
def rhd_v4_mission_control(db: Session = Depends(get_db)) -> dict[str, object]:
    return mission_control(db)


@router.get("/agent-mesh")
def rhd_v4_agent_mesh() -> dict[str, object]:
    return agent_mesh_status()


@router.post("/agent-mesh/run")
def rhd_v4_agent_run(request: AgentRunRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if request.repository_id is not None:
        _require_repo(db, request.repository_id)
    return run_supervised_read_only_plan(db, request.repository_id, request.objective, run_type="v4_read_only")


@router.get("/rag/pipeline")
def rhd_v4_rag_pipeline() -> dict[str, object]:
    return describe_rag_pipeline()


@router.post("/rag/pipeline")
def rhd_v4_rag_query(request: RagPipelineRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    _require_repo(db, request.repository_id)
    result = retrieve_agentic_evidence(db, request.repository_id, request.query, request.top_k)
    return {"pipeline": describe_rag_pipeline(), "result": result}


@router.get("/graph/neural-map/{repository_id}")
def rhd_v4_neural_map(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    _require_repo(db, repository_id)
    return neural_map(db, repository_id)


@router.get("/pr/{repository_id}/{pr_number}/risk")
def rhd_v4_pr_risk(repository_id: int, pr_number: int, db: Session = Depends(get_db)) -> dict[str, object]:
    _require_repo(db, repository_id)
    try:
        return assess_pr_risk(db, repository_id, pr_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/pr/{repository_id}/{pr_number}/blast-radius")
def rhd_v4_blast_radius(repository_id: int, pr_number: int, db: Session = Depends(get_db)) -> dict[str, object]:
    _require_repo(db, repository_id)
    try:
        return analyze_blast_radius(db, repository_id, pr_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/incidents/investigate")
def rhd_v4_incident(request: IncidentRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    _require_repo(db, request.repository_id)
    return investigate_incident(db, request.repository_id, request.query)


@router.get("/models/lab")
def rhd_v4_model_lab(db: Session = Depends(get_db)) -> dict[str, object]:
    return model_lab(db)


@router.get("/observatory")
def rhd_v4_observatory(db: Session = Depends(get_db)) -> dict[str, object]:
    return observatory(db)


@router.post("/security/probe")
def rhd_v4_security_probe(request: SecurityProbeRequest) -> dict[str, object]:
    redaction = redact_untrusted_text(request.text)
    injection = prompt_injection_guard(request.text)
    return {"redaction": redaction, "prompt_injection": injection}


def _require_repo(db: Session, repository_id: int) -> Repository:
    repo = db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
