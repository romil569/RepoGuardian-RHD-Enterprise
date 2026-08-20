# RHD v4 Baseline

Date: 2026-08-20

Branch created: `rhd-v4-intelligence`

Starting public version: `v1.1.0-public-web`

Starting commit: `2acc390`

## Repository State

- Working tree: clean before branch creation.
- Branch: `production-web` -> `rhd-v4-intelligence`.
- Remote: `enterprise-origin` -> `https://github.com/romil569/RepoGuardian-RHD-Enterprise.git`
- Protected existing tags preserved: `industry-rhd-v2-activated`, `industry-rhd-v3-enterprise`, `v1.1.0-public-web`.

## Public URLs

- Frontend: https://repoguardian-rhd.vercel.app
- Backend: https://repoguardian-rhd-api.vercel.app
- API health: https://repoguardian-rhd-api.vercel.app/health
- API readiness: https://repoguardian-rhd-api.vercel.app/readiness
- API docs: https://repoguardian-rhd-api.vercel.app/docs

## Baseline Validation

| Check | Result |
|---|---|
| Backend tests | PASS, 65 tests |
| Frontend lint | PASS |
| Frontend typecheck | PASS |
| Frontend production build | PASS, 18 static routes |
| Local Playwright | PASS, 30 tests |
| MCP typecheck | PASS |
| MCP smoke | PASS |
| Public backend `/health` | PASS |
| Public backend `/readiness` | PASS, database ready |
| Public frontend route smoke | PASS |

## Baseline Architecture

Current production is Vercel Next.js, Vercel Python FastAPI, Neon PostgreSQL, pgvector, PostgreSQL-backed staged jobs, and deterministic RHD Agentic RAG.

The v4 work must preserve the public deployment, read-only anonymous mode, deterministic fallback, explicit human approval, and Vercel + Neon compatibility.
