# RepoGuardian Architecture

## Implemented Hackathon Flow

GitHub
↓
Repository Sync
↓
Persistent Database
↓
Knowledge Index
↓
Project-Aware RAG
↓
Investigation Orchestrator
↓
Agent Tools
↓
Advanced Intelligence
↓
Priority / Escalation
↓
Evidence Validation
↓
Health / Feedback / Evaluation
↓
Maintainer Dashboard

## Current Hackathon Implementation

GitHub access is implemented through `GitHubCliService`, which wraps authenticated GitHub CLI commands. The rest of the backend depends on service methods such as `get_repository`, `get_repository_issues`, `get_issue_comments`, `get_pull_requests`, `get_releases`, and search helpers, so future GitHub App or token providers can replace the CLI adapter.

Repository synchronization stores/upserts repository metadata, issues, comments, pull requests, and releases. Repeated syncs update existing rows instead of duplicating GitHub objects.

The local data fallback uses SQLite. Production remains PostgreSQL. The vector fallback stores token vectors in `indexed_documents` and performs repository-filtered lexical/semantic scoring. Repository isolation is enforced by querying `indexed_documents.repository_id` before scoring.

The investigation orchestrator performs structured stages: load issue, classify, check context-aware completeness, retrieve repository history, run weighted duplicate detection, inspect related PRs, inspect recent releases, detect security signal, analyze release regression, calculate priority, determine escalation, validate evidence, and create the final assessment. It records an operational trace only; it does not store private model reasoning.

Prompt 3 advanced intelligence lives in `backend/app/services/advanced_intelligence.py`. It is deterministic by design so local tests can verify behavior without a live LLM. Duplicate detection combines local vector similarity, keyword overlap, category match, canonical technical terms, and temporal proximity. Completeness requirements differ by issue type. Security handling is conservative and avoids requesting public exploit or secret details. Release-regression analysis explicitly treats temporal matches as correlation, not causation.

Repository analytics expose deterministic health, weekly brief, and evaluation endpoints. Human feedback is stored in `human_feedback` and used only as labeled maintainer correction data; the evaluation endpoint reports `INSUFFICIENT_LABELED_DATA` until at least three labeled items exist.

Evidence is only displayed after validation against synchronized repository records. Fabricated source IDs, unknown source types, and cross-repository references are rejected.

The frontend provides repository connection/synchronization, repository search, issue lists with analysis status, and an investigation detail view with confidence, completeness, duplicate candidates, security signal, release-regression signal, related pull requests, priority signals, telemetry, evidence links, recommended action, feedback controls, and execution timeline. The health page presents repository score dimensions, distributions, backlog trend, weekly brief, and evaluation status. The settings page shows non-secret runtime and policy configuration.

## Future Enterprise Architecture

Future production work may add:

- GitHub App authentication
- Webhook ingestion
- Redis or queue-backed workers
- Distributed sync/indexing workers
- PostgreSQL and pgvector production deployment
- Advanced embeddings and reranking
- Policy engine for escalation
- Feedback-driven calibration dashboards
- RBAC and tenant-aware authorization
- Audit logs
- Observability and alerting
- Secure maintainer write actions

These future items are not currently implemented.
