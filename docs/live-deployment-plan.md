# Live Deployment Plan

Status: `VERCEL_AUTHORIZATION_REQUIRED`.

## Monorepo Paths

| Component | Path | Runtime |
|---|---|---|
| Frontend | `frontend/` | Vercel Next.js |
| Backend | `api/index.py` + `backend/` | Vercel Python serverless FastAPI |
| Database | Neon | PostgreSQL + pgvector |
| Jobs | `deployment_jobs` | PostgreSQL-backed staged processing |
| MCP server | `mcp-server/` | Local stdio only for public mode |

## Public Deployment Target

- Project A: `repoguardian-rhd`, root `frontend/`.
- Project B: `repoguardian-rhd-api`, root repository root, Vercel Python runtime.
- Branch: `production-web`.
- Database: existing Neon project and already validated migrations.
- Queue: Postgres job queue. Redis is not required.
- AI: deterministic RHD active without provider keys. Cloud keys are optional.

## Backend Environment

Set these only in the backend Vercel project:

- `DATABASE_URL`
- `DEPLOYMENT_MODE=MANAGED_CLOUD`
- `POSTGRES_RUNTIME_MODE=managed`
- `DATA_BACKEND=postgres`
- `VECTOR_BACKEND=pgvector`
- `QUEUE_BACKEND=postgres`
- `PUBLIC_ANALYSIS_MODE=true`
- `ENABLE_PUBLIC_WRITE_ACTIONS=false`
- `GITHUB_WRITE_MODE=disabled`
- `ENABLE_STARTUP_SCHEMA_CREATE=false`
- `AI_PROVIDER_MODE=auto`
- `DEMO_GITHUB_REPOSITORY=romil569/RepoGuardian-Demo`
- `CORS_ORIGINS=<actual frontend URL>`
- `FRONTEND_URL=<actual frontend URL>`

## Frontend Environment

Set in the frontend Vercel project:

- `NEXT_PUBLIC_API_URL=<actual backend URL>`
- `NEXT_PUBLIC_DEMO_GITHUB_REPOSITORY=romil569/RepoGuardian-Demo`

## Public Safety Defaults

- Anonymous visitors are read-only.
- No comments, labels, closes, merges, pushes, or draft PRs are executed in public mode.
- GitHub access uses the public REST API and optional server-side token only.
- RHD onboarding is staged through PostgreSQL jobs and bounded public GitHub limits.
- Large repositories are reported as `BOUNDED INITIAL REVIEW`.

## Release Gate

Create `v1.1.0-public-web` only after actual public HTTPS frontend, backend, API docs, Neon connectivity, pgvector checks, public RHD queries, and Playwright checks pass.
