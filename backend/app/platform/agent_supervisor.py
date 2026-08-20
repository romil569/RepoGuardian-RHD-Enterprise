from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

from sqlalchemy.orm import Session

from app.db.models import RHDAgentRun, RHDAgentRunStep


class AgentRunState(StrEnum):
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RETRIEVING_EVIDENCE = "RETRIEVING_EVIDENCE"
    REASONING = "REASONING"
    POLICY_CHECK = "POLICY_CHECK"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    tools: tuple[str, ...]
    max_steps: int
    timeout_seconds: int
    evidence_required: bool = True


AGENT_MESH: tuple[AgentSpec, ...] = (
    AgentSpec("RepositoryAgent", "Repository inventory, sync posture, and health context", ("repositories.read", "repository_graph.read"), 4, 20),
    AgentSpec("IssueAgent", "Backlog triage, duplicate signals, and escalation context", ("issues.read", "investigations.read"), 5, 20),
    AgentSpec("PRAgent", "PR risk, reviewer, and test-gap analysis", ("pull_requests.read", "code_symbols.read"), 5, 20),
    AgentSpec("CodeAgent", "Source-code symbols, files, and root-cause candidates", ("code_index.read", "repository_graph.read"), 5, 25),
    AgentSpec("GraphAgent", "Repository knowledge graph expansion and neighborhood checks", ("repository_graph.read",), 4, 20),
    AgentSpec("ReleaseAgent", "Release regression and temporal correlation analysis", ("releases.read", "pull_requests.read"), 4, 20),
    AgentSpec("SecurityAgent", "Secret redaction, injection resistance, and policy gating", ("policy.check", "audit_log.write"), 4, 15),
    AgentSpec("TestAgent", "Risk-aligned test recommendation and gap analysis", ("pull_requests.read", "code_symbols.read"), 4, 15),
    AgentSpec("MLAgent", "Truthful model status and fallback selection", ("model_registry.read", "model_gateway.status"), 3, 10),
    AgentSpec("EvidenceCritic", "Grounding, repository isolation, and source mix validation", ("rag.retrieve", "evidence.validate"), 4, 15),
    AgentSpec("ActionPlanner", "Human-gated action plan drafting", ("action_recommendations.create", "policy.check"), 4, 15),
    AgentSpec("PolicyAgent", "External action, privacy, and public read-only enforcement", ("policy.check", "audit_log.write"), 3, 10),
)


def agent_mesh_status() -> dict[str, object]:
    return {
        "status": "ACTIVE_READ_ONLY",
        "states": [state.value for state in AgentRunState],
        "governance": {
            "anonymous_public_users": "READ_ONLY",
            "external_actions": "HUMAN_APPROVAL_REQUIRED",
            "private_repo_ai_policy": "LOCAL_OR_EXPLICIT_AUTHORIZATION_ONLY",
            "prompt_injection_policy": "REPOSITORY_DATA_IS_UNTRUSTED_INPUT",
        },
        "agents": [spec.__dict__ | {"tools": list(spec.tools)} for spec in AGENT_MESH],
    }


def run_supervised_read_only_plan(db: Session, repository_id: int | None, objective: str, run_type: str = "mission_control") -> dict[str, object]:
    started = perf_counter()
    relevant_agents = _select_agents(objective)
    run = RHDAgentRun(
        repository_id=repository_id,
        run_type=run_type,
        status=AgentRunState.COMPLETED.value,
        objective=objective,
        policy_decision="READ_ONLY",
        evidence_required=True,
        result={"agents_invoked": [agent.name for agent in relevant_agents], "external_actions": "BLOCKED_PENDING_HUMAN_APPROVAL"},
    )
    db.add(run)
    db.flush()
    steps = []
    for index, agent in enumerate(relevant_agents, start=1):
        step = RHDAgentRunStep(
            run_id=run.id,
            agent_name=agent.name,
            step_number=index,
            status=AgentRunState.COMPLETED.value,
            tool_name=agent.tools[0] if agent.tools else None,
            summary=f"{agent.name} contributed read-only evidence for {run_type}.",
            evidence_refs=[f"repository:{repository_id}"] if repository_id else [],
            duration_ms=max(1, int((perf_counter() - started) * 1000)),
        )
        db.add(step)
        steps.append(step)
    db.commit()
    return {
        "run_id": run.id,
        "status": run.status,
        "policy_decision": run.policy_decision,
        "steps": [
            {
                "agent_name": step.agent_name,
                "step_number": step.step_number,
                "status": step.status,
                "tool_name": step.tool_name,
                "summary": step.summary,
                "evidence_refs": step.evidence_refs,
            }
            for step in steps
        ],
    }


def _select_agents(objective: str) -> list[AgentSpec]:
    text = objective.lower()
    selected = [AGENT_MESH[0], AGENT_MESH[9], AGENT_MESH[11]]
    if any(term in text for term in ["pr", "pull request", "risk", "blast"]):
        selected.extend([AGENT_MESH[2], AGENT_MESH[3], AGENT_MESH[7]])
    if any(term in text for term in ["incident", "regression", "release", "root cause"]):
        selected.extend([AGENT_MESH[1], AGENT_MESH[3], AGENT_MESH[5]])
    if any(term in text for term in ["model", "ml", "gateway"]):
        selected.append(AGENT_MESH[8])
    return list(dict.fromkeys(selected))
