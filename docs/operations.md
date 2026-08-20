# Operations Runbook

## Health Checks

- Backend liveness: `GET /health`
- Backend readiness: `GET /readiness`
- System status: `GET /api/system/status`
- Enterprise readiness: `GET /api/platform/enterprise-readiness`

## Backend Redeploy

Push to the production branch connected to Render. Render should run:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Frontend Redeploy

Push to the production branch connected to Vercel with:

```bash
NEXT_PUBLIC_API_URL=<backend-url>
```

## Database Migration

Run from `backend/` with `DATABASE_URL` set in the deployment environment:

```bash
alembic upgrade head
```

## Incident Controls

Disable public scanning:

```bash
PUBLIC_ANALYSIS_MODE=false
```

Disable external writes:

```bash
ENABLE_PUBLIC_WRITE_ACTIONS=false
```

Force deterministic-only model behavior:

```bash
AI_PROVIDER_PRIORITY=deterministic
```

Reduce abuse risk:

```bash
RATE_LIMIT_EXPENSIVE_MAX_REQUESTS=3
```

## Rollback

Redeploy the previous known-good Git commit from the hosting provider dashboard. Do not roll database migrations backward unless a reviewed downgrade exists.

## GitHub API Rate Limit

If unauthenticated public GitHub API calls rate-limit, set a scoped read-only `GITHUB_TOKEN` as a backend secret. Never expose it to the frontend.
