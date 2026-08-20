# RepoGuardian Architecture

## Current Implemented System

GitHub
↓
Sync / Monitoring
↓
SQLite or PostgreSQL abstraction
↓
Repository Knowledge Index
↓
Project-Aware RAG
↓
Investigation Orchestrator
↓
Structured Tools
↓
Duplicate / Completeness / Security / Release Analysis
↓
Priority
↓
Selective Escalation
↓
Evidence Validation
↓
Action Recommendation
↓
Human Review
↓
Policy Validation
↓
Safe GitHub Action
↓
Audit Trail
↓
Maintainer Dashboard

## Runtime Implementation

GitHub access uses `GitHubCliService`, a backend service abstraction over authenticated GitHub CLI. The frontend never shells out to GitHub and never receives credentials.

Repository synchronization upserts repository metadata, issues, comments, pull requests, and releases. Repeated syncs update existing rows instead of duplicating GitHub objects.

The hackathon runtime uses SQLite and local repository-filtered token vectors. Production architecture targets PostgreSQL and pgvector through `docker-compose.yml`, but Docker is not required for the working demo.

The RAG retriever filters by `repository_id` before scoring. This protects repository isolation and prevents cross-repository evidence leakage.

The investigation orchestrator performs bounded structured stages: load issue, classify, analyze completeness, retrieve repository history, detect duplicates, inspect PRs/releases, detect security signal, analyze release regression, calculate priority, determine escalation, validate evidence, store telemetry, and create an action recommendation.

Prompt 3 intelligence is deterministic by default. `AI_PROVIDER_MODE=auto` reports OpenAI as available only when `OPENAI_API_KEY` is configured; otherwise deterministic intelligence remains active.

Prompt 4 adds human review. Investigations create `ActionRecommendation` rows but do not execute external writes. Maintainers review previews, approve or reject, and execution validates policy again server-side. Supported actions are intentionally limited to safe label/comment/review workflows. The system does not close issues, merge PRs, delete branches, delete issues, or disclose security details.

Audit logging is append-oriented and stores safe summaries plus metadata for repository, issue, investigation, action recommendation, actor, event type, and timestamp. It does not store secrets or private reasoning.

## Enterprise Evolution

Future production architecture can add:

- GitHub App authentication and webhooks
- PostgreSQL + pgvector production deployment
- Redis/Kafka queues
- Distributed sync/indexing/investigation workers
- Managed secret storage
- RBAC and organization membership checks
- SSO
- Multi-tenancy
- Observability and alerting
- Evaluation pipelines and drift monitoring
- Enterprise policy engine
- Enterprise audit retention

These items are roadmap items, not implemented capabilities.
