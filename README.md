# RepoGuardian

RepoGuardian is an industry-oriented hackathon project for open-source maintainers. It connects to a real GitHub repository, synchronizes issues/PRs/releases, builds a repository-scoped knowledge index, investigates issues with deterministic agentic tools, and turns recommendations into a human-approved maintainer workflow.

## Problem

Maintainers often triage issues with incomplete reports, duplicates, unclear priority, and scattered project history. Naive AI assistants can make this worse if they invent evidence or act without approval.

## Solution

RepoGuardian uses project-aware retrieval, structured investigation tools, evidence validation, and a human-in-the-loop review queue. The system recommends; a maintainer controls external GitHub actions.

## Key Features

- GitHub repository connection and idempotent sync
- Repository-scoped RAG over issues, PRs, comments, and releases
- Multi-step investigation pipeline with operational trace
- Duplicate detection, completeness analysis, security signals, release-regression analysis, related PR intelligence, priority, and escalation
- Evidence-backed explanations with repository isolation
- Repository health score, weekly brief, feedback, evaluation, and telemetry
- Action recommendations, review queue, approval/rejection, policy validation, safe GitHub action execution, and audit log
- SQLite/local vector fallback for reliable hackathon demos
- PostgreSQL/pgvector Docker target for production architecture

## Architecture

GitHub -> Sync / Monitoring -> Database -> Repository Knowledge Index -> Project-Aware RAG -> Investigation Orchestrator -> Structured Tools -> Evidence Validation -> Action Recommendation -> Human Review -> Policy Validation -> Safe GitHub Action -> Audit Trail -> Maintainer Dashboard

## Tech Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- GitHub: GitHub CLI-backed service abstraction
- Demo database: SQLite
- Demo vector backend: local repository-filtered token vectors
- Production target: PostgreSQL + pgvector
- Testing: pytest, ESLint, TypeScript, Next production build

## Pages

- Overview: health, real issue counts, pending actions, recent audit events, system status
- Repositories: connect, sync, and search repository history
- Issues / Investigations: run investigations, inspect evidence, confidence, telemetry, recommendations, feedback
- Review Queue: preview, approve, reject, and execute policy-validated recommendations
- Repository Health / Weekly Brief / Evaluation: analytics from stored repository data
- Audit Log: trace recommendations, approvals, rejections, feedback, and actions
- Settings: non-secret runtime and safety policy configuration

## Setup

```powershell
cd C:\Users\HP\Desktop\RepoGuardian
copy .env.example .env
copy backend\.env.example backend\.env
```

Authenticate GitHub CLI:

```powershell
gh auth login
gh auth status
```

Install dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

cd ..\frontend
npm install
```

Run migrations:

```powershell
cd ..\backend
.\.venv\Scripts\python -m alembic upgrade head
```

## Environment Variables

Important settings are documented in `.env.example` and `backend/.env.example`.

- `DATABASE_URL`: SQLite by default for hackathon runtime
- `DATA_BACKEND`: `sqlite`
- `VECTOR_BACKEND`: `local`
- `DEMO_GITHUB_REPOSITORY`: `romil569/RepoGuardian-Demo`
- `OPENAI_API_KEY`: optional; leave unset for deterministic mode
- `AI_PROVIDER_MODE`: `auto`, `deterministic`, or `openai`
- `REQUIRE_HUMAN_APPROVAL`: defaults to `true`
- `ALLOWED_WRITE_REPOSITORY`: defaults to `romil569/RepoGuardian-Demo`

Never commit `.env`, API keys, GitHub tokens, or database credentials.

## Running

Low-friction startup:

```powershell
.\scripts\start-dev.ps1
```

Command Prompt alternative:

```cmd
scripts\start-dev.cmd
```

Manual startup:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd ..\frontend
npm run dev
```

Open:

- Frontend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:8000/health`

## Testing

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

Doctor script:

```powershell
.\scripts\doctor.ps1
```

## Demo

Use `docs/demo-runbook.md` and `docs/demo-script.md`. The demo is deterministic and does not require Docker, pgvector, or OpenAI credentials.

Core demo path:

1. Overview dashboard
2. Repository sync/search
3. Incomplete issue investigation
4. Duplicate/regression investigation with verified evidence
5. Security-sensitive issue with urgent review
6. Review Queue action preview and approval safeguard
7. Audit Log
8. Repository Health and Weekly Brief

## Safety

- Repository writes are allow-listed to the configured demo repository.
- External GitHub writes require explicit approval and server-side policy validation.
- Evidence must correspond to synchronized repository records.
- Security-sensitive issues avoid public exploit or secret requests.
- Frontend never receives GitHub/OpenAI secrets.
- Audit logs store safe summaries, not secrets or private reasoning.

## Current Limitations

- Docker/PostgreSQL/pgvector has not been live-validated on this machine because Docker is unavailable.
- `OPENAI_API_KEY` is not configured, so deterministic intelligence is active.
- Real GitHub write validation was intentionally skipped to avoid unnecessary demo repository noise; write execution is covered by mocked tests and safe `NO_ACTION` live workflow validation.

## Enterprise Roadmap

Future production work can add GitHub App identity, webhooks, PostgreSQL/pgvector deployment, Redis/Kafka queues, distributed workers, managed secret storage, RBAC, SSO, multi-tenant isolation, observability, evaluation pipelines, and enterprise audit retention.
