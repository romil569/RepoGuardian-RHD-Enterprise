from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.rag.agentic import retrieve_agentic_evidence
from app.services import rhd
from app.services.advanced_intelligence import repository_health


class ToolSafety(StrEnum):
    READ = "read"
    ANALYZE = "analyze"
    RECOMMEND = "recommend"
    WRITE_GATED = "write_gated"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    safety: ToolSafety
    input_schema: dict[str, Any]
    handler: Callable[[Session, dict[str, Any]], dict[str, Any]]
    requires_approval: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


def _required(*names: str) -> dict[str, Any]:
    return {"type": "object", "required": list(names), "properties": {name: {"type": "string"} for name in names}}


def _repository_id(payload: dict[str, Any]) -> int:
    return int(payload["repository_id"])


def _connect_repository(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return rhd.onboard_repository(db, str(payload["repository"]), run_sync=bool(payload.get("run_sync", False)))


def _sync_repository(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.github_sync import sync_repository

    return sync_repository(db, _repository_id(payload))


def _full_review(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return rhd.full_repository_review(db, _repository_id(payload))


def _search_repository(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return retrieve_agentic_evidence(db, _repository_id(payload), str(payload["query"]), int(payload.get("top_k", 8)))


def _investigate_issue(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.agents.workflows.investigation import investigate_issue

    return investigate_issue(db, _repository_id(payload), int(payload["issue_id"]))


def _health_review(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return repository_health(db, _repository_id(payload))


def _daily_priorities(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return {"priorities": rhd.top_actions(db, _repository_id(payload), int(payload.get("limit", 5)))}


def _answer_question(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return rhd.answer_question(db, _repository_id(payload), str(payload["question"]))


def _review_queue(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.db.models import ActionRecommendation
    from app.services.action_recommendations import recommendation_dict

    rows = db.query(ActionRecommendation).filter_by(repository_id=_repository_id(payload)).order_by(ActionRecommendation.created_at.desc()).limit(25).all()
    return {"recommendations": [recommendation_dict(item) for item in rows]}


def _prepare_action(_db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "WRITE_GATED",
        "requires_approval": True,
        "requested_action": payload,
        "message": "RepoGuardian prepares external actions for human approval; it does not execute them from the tool registry.",
    }


def tool_registry() -> dict[str, ToolSpec]:
    repository_schema = _required("repository_id")
    return {
        "rhd_connect_repository": ToolSpec("rhd_connect_repository", "Connect a GitHub repository by owner/name or URL.", ToolSafety.ANALYZE, _required("repository"), _connect_repository, tags=("github", "repository")),
        "rhd_sync_repository": ToolSpec("rhd_sync_repository", "Synchronize repository issues, PRs, releases, and indexed evidence.", ToolSafety.ANALYZE, repository_schema, _sync_repository, tags=("github", "sync")),
        "rhd_full_review": ToolSpec("rhd_full_review", "Run a repository-scoped RHD review.", ToolSafety.ANALYZE, repository_schema, _full_review, tags=("rhd", "review")),
        "rhd_search_repository": ToolSpec("rhd_search_repository", "Run agentic hybrid RAG over repository evidence.", ToolSafety.READ, _required("repository_id", "query"), _search_repository, tags=("rag", "search")),
        "rhd_investigate_issue": ToolSpec("rhd_investigate_issue", "Investigate one synchronized issue.", ToolSafety.ANALYZE, _required("repository_id", "issue_id"), _investigate_issue, tags=("issue", "agent")),
        "rhd_health_review": ToolSpec("rhd_health_review", "Return repository health metrics.", ToolSafety.READ, repository_schema, _health_review, tags=("health",)),
        "rhd_daily_priorities": ToolSpec("rhd_daily_priorities", "Rank maintainer priorities from repository evidence.", ToolSafety.RECOMMEND, repository_schema, _daily_priorities, tags=("priorities", "manager")),
        "rhd_generate_report": ToolSpec("rhd_generate_report", "Answer an evidence-grounded RHD question.", ToolSafety.ANALYZE, _required("repository_id", "question"), _answer_question, tags=("rhd", "report")),
        "rhd_get_review_queue": ToolSpec("rhd_get_review_queue", "List human-gated action recommendations.", ToolSafety.READ, repository_schema, _review_queue, tags=("governance", "review")),
        "rhd_prepare_action": ToolSpec("rhd_prepare_action", "Prepare but never execute a gated external action.", ToolSafety.WRITE_GATED, _required("repository_id", "action_type"), _prepare_action, requires_approval=True, tags=("governance", "write-gated")),
    }


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "safety": spec.safety.value,
            "input_schema": spec.input_schema,
            "requires_approval": spec.requires_approval,
            "tags": list(spec.tags),
        }
        for spec in tool_registry().values()
    ]


def execute_tool(db: Session, name: str, payload: dict[str, Any], approved: bool = False) -> dict[str, Any]:
    spec = tool_registry().get(name)
    if not spec:
        raise ValueError(f"Unknown RHD tool: {name}")
    if spec.requires_approval and not approved:
        return {"status": "APPROVAL_REQUIRED", "tool": name, "safety": spec.safety.value}
    _validate_payload(spec, payload)
    return spec.handler(db, payload)


def _validate_payload(spec: ToolSpec, payload: dict[str, Any]) -> None:
    for field_name in spec.input_schema.get("required", []):
        if field_name not in payload:
            raise ValueError(f"Missing required field for {spec.name}: {field_name}")
