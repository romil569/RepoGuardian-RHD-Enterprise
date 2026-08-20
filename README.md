# RepoGuardian

RepoGuardian is an industry-oriented AI/ML hackathon project for an agentic open-source maintainer assistant. It synchronizes real GitHub repository data, indexes repository-specific history, retrieves evidence with repository isolation, and runs multi-step issue investigations with confidence, priority, escalation, and evidence validation.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL with pgvector-ready Docker Compose
- Local fallback: SQLite plus repository-filtered local lexical vectors when Docker is unavailable
- Testing: pytest, frontend lint, TypeScript checking, Next.js build

## Current Features

- `GET /health`
- `GET /api/system/status`
- `POST /api/repositories/connect`
- `POST /api/repositories/{id}/sync`
- `GET /api/repositories/{id}/issues`
- `GET /api/repositories/{id}/pull-requests`
- `GET /api/repositories/{id}/releases`
- `POST /api/repositories/{id}/search`
- `POST /api/issues/{id}/investigate`
- `GET /api/repositories/{id}/health`
- `GET /api/repositories/{id}/brief/weekly`
- `GET /api/repositories/{id}/evaluation`
- `POST /api/investigations/{id}/feedback`
- `GET /api/investigations/{id}/feedback`
- `GET /api/settings/policy`
- `GET /api/review-queue`
- `GET /api/action-recommendations/{id}`
- `POST /api/action-recommendations/{id}/approve`
- `POST /api/action-recommendations/{id}/reject`
- `POST /api/action-recommendations/{id}/execute`
- `GET /api/audit-log`
- Repository, issue, PR, release, document, investigation, evidence, escalation, and trace models
- Human feedback model for labeled maintainer corrections
- Human-in-the-loop action recommendations, review queue, approval/rejection workflow, safe action execution, and audit logging
- GitHub CLI-backed local integration
- Project-aware retrieval with repository filtering
- Multi-step deterministic investigation pipeline with advanced duplicate, completeness, priority, security, release-regression, related PR, telemetry, and escalation signals
- Repository health score, weekly brief, and evaluation metrics
- Frontend repository sync/search, investigation, review queue, audit log, feedback, health, weekly brief, evaluation, and settings UI
- Docker Compose configuration for local PostgreSQL and pgvector

## Demo Repository

The required GitHub demo repository is `RepoGuardian-Demo`. Automated write actions during development must be restricted to the repository configured as `DEMO_GITHUB_REPOSITORY`.

## Windows Local Setup

Authenticate GitHub CLI with:

```powershell
gh auth login
gh auth status
```

Create backend environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Start PostgreSQL when Docker Desktop is available:

```powershell
docker compose up -d postgres
```

Run migrations:

```powershell
cd backend
.\.venv\Scripts\python -m alembic upgrade head
```

When Docker is unavailable, use the default fallback:

```powershell
DATABASE_URL=sqlite:///./repoguardian-prompt2.db
DATA_BACKEND=sqlite
VECTOR_BACKEND=local
```

Start backend:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Start frontend:

```powershell
cd frontend
npm run dev
```

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

## Safety Restrictions

- Do not commit secrets.
- Do not put real credentials in `.env.example`.
- Do not modify repositories other than `DEMO_GITHUB_REPOSITORY`.
- Do not fabricate GitHub evidence or pretend API calls succeeded without verification.
- Automated writes are restricted to `DEMO_GITHUB_REPOSITORY`.
- Evidence shown by investigations must correspond to synchronized repository records.

## Demo Flow

1. Start the backend.
2. Open the frontend.
3. Go to Repositories.
4. Connect `romil569/RepoGuardian-Demo`.
5. Sync the repository.
6. Search for repository history such as `authentication fails after latest update`.
7. Go to Investigations and run analysis on synchronized issues.
8. Review duplicate, security, regression, priority, telemetry, evidence, and feedback panels.
9. Go to Repository Health for the score, weekly brief, and evaluation status.
10. Open Review Queue to inspect the exact proposed action payload before approval.
11. Open Audit Log to show traceability for recommendations, approvals, rejections, and executed actions.

## Next Development Stages

Future stages can add a GitHub App, webhooks, live LLM provider calls, pgvector production indexing, background workers, richer policy engines, audit logs, authenticated maintainer workflows, notification routing, and organization-wide benchmarking.
