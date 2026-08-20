# RepoGuardian RHD v4 Architecture

RepoGuardian powered by RHD is an autonomous engineering intelligence platform with evidence-grounded decisions and human-controlled execution.

## Production Shape

The public deployment remains:

- Vercel Next.js frontend
- Vercel Python FastAPI backend
- Neon PostgreSQL with pgvector readiness
- PostgreSQL-backed staged jobs
- Deterministic RHD Agentic RAG fallback

No Docker, Redis, Ollama, or separate graph database is required for the public demo.

## v4 Additions

| Layer | Implementation | Status |
|---|---|---|
| Agent Mesh | `RepositoryAgent`, `IssueAgent`, `PRAgent`, `CodeAgent`, `GraphAgent`, `ReleaseAgent`, `SecurityAgent`, `TestAgent`, `MLAgent`, `EvidenceCritic`, `ActionPlanner`, `PolicyAgent` | Beta, read-only |
| Agent Traces | `rhd_agent_runs`, `rhd_agent_run_steps` | Implemented |
| Model Gateway | Task enum for intent, planning, PR risk, blast radius, incidents, tests, policy, evaluation | Implemented |
| Model Telemetry | `model_provider_telemetry` table for provider/task/status/latency | Implemented schema |
| Code Intelligence | `code_symbol_index` plus existing bounded scanner | Beta |
| PR Intelligence | Deterministic risk, blast radius, reviewer hints, test recommendations | Beta |
| Incident Intelligence | Timeline and hypotheses over synced issues, PRs, releases, events, and RAG evidence | Beta |
| RAG Pipeline | Planner, hybrid retrieval, score fusion, deterministic reranking, graph/code expansion, grounding critic | Implemented |
| Observatory | Audit, conversation, model telemetry, PR risk, and incident counters | Implemented |

## API Surface

- `GET /api/v4/mission-control`
- `GET /api/v4/agent-mesh`
- `POST /api/v4/agent-mesh/run`
- `GET /api/v4/rag/pipeline`
- `POST /api/v4/rag/pipeline`
- `GET /api/v4/graph/neural-map/{repository_id}`
- `GET /api/v4/pr/{repository_id}/{pr_number}/risk`
- `GET /api/v4/pr/{repository_id}/{pr_number}/blast-radius`
- `POST /api/v4/incidents/investigate`
- `GET /api/v4/models/lab`
- `GET /api/v4/observatory`
- `POST /api/v4/security/probe`

## Governance

- Public users remain read-only.
- Private repository content is not sent to external AI providers without explicit authorization.
- Repository text is untrusted input.
- README, issue, PR, comment, and code content cannot override system policy.
- External GitHub writes remain human-gated through action recommendations.
- No PR merge, issue close, branch delete, or generated code push occurs automatically.

## Truth Policy

Predictive ML and deep learning are represented through model cards. The public product reports deterministic fallback until enough defensible labeled data exists and training/validation is actually run. Cross-encoder reranking is documented as optional; deterministic reranking remains the active public behavior unless a configured model is available.
