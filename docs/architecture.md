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
Priority / Escalation
↓
Evidence Validation
↓
Maintainer Dashboard

## Current Hackathon Implementation

GitHub access is implemented through `GitHubCliService`, which wraps authenticated GitHub CLI commands. The rest of the backend depends on service methods such as `get_repository`, `get_repository_issues`, `get_issue_comments`, `get_pull_requests`, `get_releases`, and search helpers, so future GitHub App or token providers can replace the CLI adapter.

Repository synchronization stores/upserts repository metadata, issues, comments, pull requests, and releases. Repeated syncs update existing rows instead of duplicating GitHub objects.

The local data fallback uses SQLite. Production remains PostgreSQL. The vector fallback stores token vectors in `indexed_documents` and performs repository-filtered lexical/semantic scoring. Repository isolation is enforced by querying `indexed_documents.repository_id` before scoring.

The investigation orchestrator performs structured stages: load issue, classify, check completeness, retrieve repository history, search similar issues, inspect related PRs, inspect recent releases, calculate priority, determine escalation, validate evidence, and create the final assessment. It records an operational trace only; it does not store private model reasoning.

Evidence is only displayed after validation against synchronized repository records. Fabricated source IDs, unknown source types, and cross-repository references are rejected.

The frontend provides repository connection/synchronization, repository search, issue lists with analysis status, and an investigation detail view with confidence, completeness, related context, evidence links, recommended action, and execution timeline.

## Future Enterprise Architecture

Future production work may add:

- GitHub App authentication
- Webhook ingestion
- Redis or queue-backed workers
- Distributed sync/indexing workers
- PostgreSQL and pgvector production deployment
- Advanced embeddings and reranking
- Policy engine for escalation
- RBAC and tenant-aware authorization
- Audit logs
- Observability and alerting
- Secure maintainer write actions

These future items are not currently implemented.
