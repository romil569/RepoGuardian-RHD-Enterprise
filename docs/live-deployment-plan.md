# Live Deployment Plan

Status: `READY_FOR_ACCOUNT_AUTHORIZATION`.

## Monorepo Paths

| Component | Path | Runtime |
|---|---|---|
| Frontend | `frontend/` | Next.js 16, Node 24 locally, Node 22 in CI |
| Backend | `backend/` | FastAPI, Python 3.12 |
| Worker | `backend/Dockerfile.worker` | Optional container worker |
| MCP server | `mcp-server/` | TypeScript MCP stdio server |

FastAPI import path:

```bash
app.main:app
```

Production backend command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Frontend build command:

```bash
npm run build
```

## Public Deployment Target

- Frontend: Vercel project rooted at `frontend/`.
- Backend: Render Python web service rooted at `backend/`.
- Database: managed PostgreSQL with `DATABASE_URL`.
- Vector extension: pgvector, validated by `/api/platform/enterprise-readiness`.
- Queue: Postgres queue fallback for first public deployment; Redis remains optional.
- AI: deterministic RHD active without cloud AI keys; cloud providers optional.

## Required Secrets

These must be entered in hosting provider environment-variable UI or CLI secret storage, never in source:

- `DATABASE_URL`
- optional `GITHUB_TOKEN`
- optional `GROQ_API_KEY`
- optional `OPENROUTER_API_KEY`
- optional `OPENAI_API_KEY`

## Public Safety Defaults

- `PUBLIC_ANALYSIS_MODE=true`
- `ENABLE_PUBLIC_WRITE_ACTIONS=false`
- public repositories only for anonymous visitors
- bounded rate limiting for onboarding, sync, investigations, and RHD queries
- deterministic RHD remains available when cloud AI is not configured

## Validation Before Release Tag

The final `v1.1.0-public-web` tag should be created only after actual public HTTPS frontend, backend, API docs, database, readiness, and public Playwright checks pass.
