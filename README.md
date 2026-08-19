# RepoGuardian

RepoGuardian is an industry-oriented AI/ML hackathon foundation for an agentic open-source maintainer assistant. Prompt 1 bootstraps the safe project shell, demo repository, backend, frontend, database configuration, and verification docs.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL with pgvector-ready Docker Compose
- Testing: pytest, frontend lint, TypeScript checking, Next.js build

## Current Features

- `GET /health`
- `GET /api/system/status`
- Repository model and Alembic migration
- Demo repository allow-list configuration
- Professional dashboard shell with empty states
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

## Next Development Stages

Prompt 2 can add authenticated GitHub ingestion, issue analysis, repository context retrieval, RAG, agent workflows, persistence, and guarded write actions. A fine-grained GitHub token may be needed then, restricted only to `RepoGuardian-Demo` with minimum necessary permissions.
