from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    ActionRecommendation,
    AuditLogEvent,
    CodeSymbolIndex,
    ConversationMessage,
    IncidentInvestigation,
    Issue,
    ModelProviderTelemetry,
    PRRiskAssessment,
    PullRequest,
    Repository,
    RepositoryGraphEdge,
    RepositoryGraphNode,
)
from app.ml.registry import model_status_cards
from app.platform.model_gateway import ModelGateway, ModelTask


def mission_control(db: Session) -> dict[str, object]:
    repo_count = db.query(func.count(Repository.id)).scalar() or 0
    issue_count = db.query(func.count(Issue.id)).scalar() or 0
    pr_count = db.query(func.count(PullRequest.id)).scalar() or 0
    pending_actions = db.query(func.count(ActionRecommendation.id)).filter(ActionRecommendation.status == "PENDING").scalar() or 0
    return {
        "positioning": {
            "name": "RepoGuardian",
            "powered_by": "RHD - Repository Health Director",
            "tagline": "Autonomous Engineering Intelligence. Evidence-grounded decisions. Human-controlled execution.",
        },
        "operating_mode": "PUBLIC_READ_ONLY" if pending_actions == 0 else "HUMAN_REVIEW_REQUIRED",
        "inventory": {"repositories": repo_count, "issues": issue_count, "pull_requests": pr_count, "pending_human_actions": pending_actions},
        "v4_capabilities": [
            {"name": "Agent Mesh", "status": "ACTIVE_READ_ONLY"},
            {"name": "Agentic/Hybrid RAG", "status": "ACTIVE_DETERMINISTIC"},
            {"name": "PR Risk and Blast Radius", "status": "ACTIVE_WITH_SYNCED_PR_DATA"},
            {"name": "Incident Intelligence", "status": "ACTIVE_WITH_REPOSITORY_EVIDENCE"},
            {"name": "Predictive ML", "status": "DETERMINISTIC_FALLBACK_UNTIL_ENOUGH_LABELS"},
        ],
    }


def neural_map(db: Session, repository_id: int) -> dict[str, object]:
    nodes = db.query(RepositoryGraphNode).filter_by(repository_id=repository_id).limit(60).all()
    edges = db.query(RepositoryGraphEdge).filter_by(repository_id=repository_id).limit(120).all()
    symbols = db.query(CodeSymbolIndex).filter_by(repository_id=repository_id).limit(40).all()
    return {
        "repository_id": repository_id,
        "status": "GRAPH_AVAILABLE" if nodes or symbols else "AWAITING_GRAPH_OR_CODE_INDEX",
        "nodes": [{"node_id": node.node_id, "labels": node.labels, "properties": node.properties} for node in nodes]
        + [{"node_id": f"symbol:{symbol.id}", "labels": ["CodeSymbol"], "properties": {"name": symbol.symbol_name, "type": symbol.symbol_type, "file_path": symbol.file_path}} for symbol in symbols],
        "edges": [{"source": edge.source_node_id, "target": edge.target_node_id, "type": edge.edge_type, "properties": edge.properties} for edge in edges],
    }


def model_lab(db: Session) -> dict[str, object]:
    gateway = ModelGateway.from_settings()
    telemetry_count = db.query(func.count(ModelProviderTelemetry.id)).scalar() or 0
    return {
        "gateway": {"priority": gateway.priority, "providers": gateway.status(), "tasks": [task.value for task in ModelTask]},
        "model_cards": [card.__dict__ | {"status": card.status.value} for card in model_status_cards()],
        "telemetry_rows": telemetry_count,
        "truth_policy": "No custom training metrics are reported until training and validation data exists.",
    }


def observatory(db: Session) -> dict[str, object]:
    return {
        "events": {
            "audit_log": db.query(func.count(AuditLogEvent.id)).scalar() or 0,
            "conversations": db.query(func.count(ConversationMessage.id)).scalar() or 0,
            "model_telemetry": db.query(func.count(ModelProviderTelemetry.id)).scalar() or 0,
            "pr_risk_assessments": db.query(func.count(PRRiskAssessment.id)).scalar() or 0,
            "incident_investigations": db.query(func.count(IncidentInvestigation.id)).scalar() or 0,
        },
        "slo": {"public_read_api": "best_effort", "external_actions": "human_gated", "ai_provider_failure": "deterministic_fallback"},
    }
