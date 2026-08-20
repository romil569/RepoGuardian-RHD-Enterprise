# RepoGuardian Agent Notes

RepoGuardian is an agentic open-source maintainer assistant. Prompt 2 implements the compulsory hackathon pipeline: GitHub sync, repository-scoped indexing, project-aware RAG, deterministic agent tools, multi-step issue investigation, selective escalation, and evidence validation. Prompt 3 extends that pipeline with advanced duplicate detection, context-aware completeness, priority scoring, security signals, release-regression analysis, related PR intelligence, repository health, weekly brief, human feedback, evaluation metrics, and telemetry. Prompt 4 adds a human-in-the-loop maintainer workflow with safe action recommendations, review queue, approval/rejection, policy validation, GitHub action execution guards, and audit logging.

## Architecture

- `backend/`: FastAPI, Pydantic settings, SQLAlchemy models, Alembic migrations, service placeholders.
- `backend/app/github/client.py`: GitHub service interface currently backed by authenticated GitHub CLI for local development.
- `backend/app/services/github_sync.py`: repository connect/sync/upsert pipeline.
- `backend/app/services/indexing.py`: converts issues, PRs, comments, and releases into indexed repository documents.
- `backend/app/rag/retriever.py`: repository-filtered local vector/keyword retrieval fallback.
- `backend/app/agents/tools/analysis.py`: structured deterministic tools for classification, completeness, priority, escalation, similar issues, PRs, and releases.
- `backend/app/agents/workflows/investigation.py`: multi-step orchestrator with safe operational trace.
- `backend/app/services/advanced_intelligence.py`: deterministic Prompt 3 intelligence engines and repository analytics.
- `backend/app/api/routes/analytics.py`: health, weekly brief, and evaluation endpoints.
- `backend/app/api/routes/investigations.py`: human feedback endpoints for completed investigations.
- `backend/app/api/routes/settings.py`: non-secret policy settings endpoint.
- `backend/app/services/action_recommendations.py`: Prompt 4 recommendation, policy, approval, execution, and idempotency logic.
- `backend/app/services/audit.py`: append-oriented safe audit events.
- `backend/app/api/routes/action_recommendations.py`: review queue and action workflow endpoints.
- `backend/app/api/routes/audit_log.py`: audit log API.
- `backend/app/services/evidence.py`: strict evidence source validation.
- `frontend/`: Next.js, TypeScript, Tailwind CSS, repository sync/search UI, investigation UI, health dashboards, feedback controls, and non-secret settings panels.
- `infrastructure/`: database initialization and future deployment assets.
- `docs/`: setup reports and architecture notes.
- `demo/`: harmless local demo source material.

## Local Commands

- Backend setup: `cd backend && python -m venv .venv && .\.venv\Scripts\python -m pip install -r requirements.txt`
- Backend tests: `cd backend && .\.venv\Scripts\python -m pytest`
- Backend dev server: `cd backend && .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000`
- Frontend setup: `cd frontend && npm install`
- Frontend lint/type/build: `npm run lint`, `npm run typecheck`, `npm run build`
- Frontend dev server: `cd frontend && npm run dev`
- Database: `docker compose up -d postgres`
- Migrations: `cd backend && .\.venv\Scripts\python -m alembic upgrade head`
- Connect demo repository: `POST /api/repositories/connect` with `{"repository":"romil569/RepoGuardian-Demo"}`
- Sync repository: `POST /api/repositories/{id}/sync`
- Search repository history: `POST /api/repositories/{id}/search`
- Investigate issue: `POST /api/issues/{id}/investigate`
- Repository health: `GET /api/repositories/{id}/health`
- Weekly brief: `GET /api/repositories/{id}/brief/weekly`
- Evaluation: `GET /api/repositories/{id}/evaluation`
- Feedback: `POST /api/investigations/{id}/feedback`
- Review queue: `GET /api/review-queue`
- Approve/reject/execute: `POST /api/action-recommendations/{id}/approve`, `/reject`, `/execute`
- Audit log: `GET /api/audit-log`

## Data Backends

- Production target: PostgreSQL plus pgvector via `docker-compose.yml`.
- Local fallback: SQLite plus repository-filtered lexical vectors stored in `indexed_documents`.
- Use `DATA_BACKEND` and `VECTOR_BACKEND` to document/select the active mode.
- Repository filtering must happen inside retrieval queries before scoring. Do not retrieve globally and filter afterward.

## Safety Rules

- Only the repository configured by `DEMO_GITHUB_REPOSITORY` may be modified by automated development/test actions.
- The demo repository is expected to be `<authenticated-user>/RepoGuardian-Demo`.
- Never modify issues, labels, branches, pull requests, or releases in non-demo repositories unless the user explicitly requests it.
- Never fabricate GitHub evidence, commits, labels, issue contents, or release history in reports.
- Every displayed evidence item must be verified against synchronized repository records or a verified GitHub response.
- Never commit `.env`, tokens, API keys, browser cookies, or credentials.
- Preserve repository isolation and run relevant tests after meaningful changes.
- Live AI provider calls require `OPENAI_API_KEY`; without it, deterministic tools must return `AI provider not configured` behavior rather than fabricating AI output.
- Policy settings exposed to the frontend must stay non-secret.
- External GitHub writes must go through `ActionRecommendation` approval and server-side policy validation.
- Prompt 4 uses `local-maintainer` as a hackathon reviewer identity only; do not describe it as production RBAC.
