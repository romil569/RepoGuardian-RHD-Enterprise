# Vercel Backend Audit

Status: `IMPLEMENTED_FOR_PUBLIC_DEMO`.

## Entrypoint

- Existing app: `backend/app/main.py`, object `app`.
- Vercel entrypoint: `api/index.py`.
- Business logic remains in `backend/app`; `api/index.py` only adjusts `sys.path` and imports the app.

## Serverless Compatibility Findings

| Area | Finding | Resolution |
|---|---|---|
| Startup hooks | App previously created tables and started scheduler in lifespan. | Managed cloud skips scheduler; schema creation can be disabled with `ENABLE_STARTUP_SCHEMA_CREATE=false`. |
| Migrations | Running Alembic on every request would be unsafe. | Migrations are explicit one-time commands. Neon is already migrated. |
| Database pooling | Serverless can create many instances. | Managed PostgreSQL uses bounded SQLAlchemy pools, `pool_pre_ping`, timeout, and recycle settings. |
| Queue | Prior Postgres queue class used in-memory fallback. | Added `deployment_jobs` table and `PostgresJobQueue` persistence. |
| Onboarding | Previous RHD onboarding did sync/review inline. | Managed cloud returns a job and advances bounded stages through `/api/jobs/{id}/advance`. |
| Rate limiting | Prior public limiter was process memory. | Added PostgreSQL `public_rate_limit_events` storage with local fallback. |
| Sessions | RHD context was client supplied/in-memory-like. | Added `public_sessions` and `conversation_messages` with repository-scoped opaque session IDs. |
| Filesystem | Code scan accepted local paths. | Serverless mode rejects local filesystem code scanning. |
| Graph | Local graph store was process memory only. | Added `repository_graph_nodes` and `repository_graph_edges` plus `PostgresGraphStore`. |
| GitHub | CLI is unavailable in Vercel. | Public mode uses `GitHubRestService`; optional token is server-side only. |
| AI/Ollama | Cloud must not call localhost. | Ollama provider is local-only when `settings.is_serverless`; deterministic fallback remains active. |
| Writes | Public deployment must be read-only. | Route and service guards enforce `ENABLE_PUBLIC_WRITE_ACTIONS=false` and `GITHUB_WRITE_MODE=disabled`. |

## Active Public Limits

- `MAX_PUBLIC_ISSUES`
- `MAX_PUBLIC_PRS`
- `MAX_PUBLIC_RELEASES`
- `MAX_INITIAL_CODE_FILES`
- `MAX_INITIAL_CODE_BYTES`
- `MAX_CODE_FILE_BYTES`
- `MAX_RHD_STEPS`
- `MAX_RETRIEVAL_RESULTS`

The initial serverless sync is bounded. When limits are reached, responses mark the run as `BOUNDED INITIAL REVIEW`.

## Remaining Operational Notes

The current staged job processor advances one bounded stage per API call. For very large repositories, future work can split GitHub issue, PR, and code indexing into cursor-based sub-stages, but the public demo no longer relies on a permanent worker or Redis.
