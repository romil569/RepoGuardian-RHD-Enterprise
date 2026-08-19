# RepoGuardian Agent Notes

RepoGuardian is a Prompt 1 foundation for an agentic open-source maintainer assistant. Do not implement full RAG, AI investigation, automated writes, or evidence synthesis without an explicit later prompt.

## Architecture

- `backend/`: FastAPI, Pydantic settings, SQLAlchemy models, Alembic migrations, service placeholders.
- `frontend/`: Next.js, TypeScript, Tailwind CSS, dashboard shell and empty states.
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

## Safety Rules

- Only the repository configured by `DEMO_GITHUB_REPOSITORY` may be modified by automated development/test actions.
- The demo repository is expected to be `<authenticated-user>/RepoGuardian-Demo`.
- Never modify issues, labels, branches, pull requests, or releases in non-demo repositories unless the user explicitly requests it.
- Never fabricate GitHub evidence, commits, labels, issue contents, or release history in reports.
- Never commit `.env`, tokens, API keys, browser cookies, or credentials.
- Preserve repository isolation and run relevant tests after meaningful changes.
