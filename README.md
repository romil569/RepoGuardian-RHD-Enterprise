# RepoGuardian

## powered by RHD - Repository Health Director

### Autonomous Software Engineering Intelligence with Human-Controlled Execution

[![Python](https://img.shields.io/badge/Python-3.12-blue)](backend)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)](backend/app/main.py)
[![Next.js](https://img.shields.io/badge/Next.js-frontend-black)](frontend)
[![TypeScript](https://img.shields.io/badge/TypeScript-checked-3178c6)](frontend)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-managed--ready-336791)](docs/deployment-managed-cloud.md)
[![pgvector](https://img.shields.io/badge/pgvector-ready--not--connected-5b46c8)](docs/deployment-managed-cloud.md)
[![MCP](https://img.shields.io/badge/MCP-stdio--implemented-4b5563)](mcp-server)
[![Ollama](https://img.shields.io/badge/Ollama-local--validated-7c3aed)](docs/provider-benchmark.md)
[![Tests](https://img.shields.io/badge/tests-pytest%20%7C%20playwright%20%7C%20mcp-brightgreen)](#testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Connect a GitHub repository. RHD investigates its issues, pull requests, source code, releases, engineering risks and repository health using agentic RAG, specialized ML intelligence and evidence-grounded reasoning.

RHD analyzes automatically. RHD recommends automatically. Humans authorize external actions.

## Live Application

Public web app: https://repoguardian-rhd.vercel.app

FastAPI: https://repoguardian-rhd-api.vercel.app

API docs: https://repoguardian-rhd-api.vercel.app/docs

Architecture: https://repoguardian-rhd.vercel.app/architecture

## Architecture

```mermaid
flowchart LR
  G[GitHub] --> W[Webhooks / Sync]
  W --> Q[Event Queue]
  Q --> RI[Repository Intelligence]
  RI --> S[(SQL + Vector + Graph)]
  S --> AR[Agentic RAG]
  AR --> RHD[RHD Supervisor]
  RHD --> A[Specialist Agents]
  A --> ML[ML / DL Intelligence]
  ML --> EC[Evidence Critic]
  EC --> PG[Policy Gate]
  PG --> HR[Human Review]
  HR --> GA[GitHub Action]
```

Deployment modes:

- `LIGHTWEIGHT_LOCAL`: SQLite, local vectors, deterministic/RHD tools.
- `INDUSTRY_LOCAL`: optional Docker PostgreSQL/Redis when Docker exists.
- `MANAGED_CLOUD`: Vercel frontend, Vercel Python FastAPI backend, Neon PostgreSQL/pgvector, Postgres queue.
- `ENTERPRISE_AWS`: Terraform foundation; not provisioned.

## Feature Matrix

| Feature | Status | Notes |
|---|---|---|
| RHD Agent | Working | Repository review, Ask RHD, priorities, evidence trace |
| Agentic RAG v2 | Implemented | Query planner, hybrid retrieval, critic, objective eval metrics |
| Code-RAG | Partial | Static code scan/symbol graph foundations; deep code embeddings optional |
| Graph-RAG | Partial | Local graph abstraction and evidence paths; production graph DB not connected |
| MCP Server | Implemented | stdio tools/resources/prompts over shared RHD tool registry |
| PR Risk | Working | PR activity and related PR intelligence foundations |
| Issue Intelligence | Working | Duplicate, completeness, priority, security, release correlation |
| Security Signals | Working | Signal detection only; not vulnerability certification |
| Release Intelligence | Working | Correlation wording, no causation claims |
| Repository Health | Working | Health score, dimensions, weekly brief |
| Automation | Partial | Event/job foundations; no unrestricted autopilot |
| Review Queue | Working | Approval, rejection, policy validation |
| Audit | Working | Safe summaries, no secrets |
| Model Gateway | Working | Ollama local adapter, cloud config probes, deterministic fallback |
| ML Registry | Working | Honest model cards; training requires defensible dataset |
| Managed PostgreSQL | Neon validated | Provider-neutral `DATABASE_URL`, pgvector health checks |
| Serverless Queue | Implemented | Postgres job queue for Vercel; local fallback remains available |

## Quick Start

### Lightweight Local

```powershell
cd C:\Users\HP\Desktop\RepoGuardian
copy .env.example .env
copy backend\.env.example backend\.env
.\scripts\start-dev.ps1
```

Open `http://127.0.0.1:3000`.

### Industry Local

```powershell
cd C:\Users\HP\Desktop\RepoGuardian
.\scripts\start-industry-local.ps1
.\scripts\doctor.ps1
```

Docker PostgreSQL/Redis are used only when Docker is installed. Otherwise the stable lightweight path remains available.

### Managed Cloud

Backend Vercel entrypoint: `api/index.py`.

Required backend environment:

- `DEPLOYMENT_MODE=MANAGED_CLOUD`
- `DATABASE_URL=postgresql://...`
- `POSTGRES_RUNTIME_MODE=managed`
- `QUEUE_BACKEND=postgres`
- `PUBLIC_ANALYSIS_MODE=true`
- `GITHUB_WRITE_MODE=disabled`
- `FRONTEND_URL=https://...`
- `CORS_ORIGINS=https://...`
- `ENABLE_STARTUP_SCHEMA_CREATE=false`

Frontend environment:

```bash
NEXT_PUBLIC_API_URL=https://your-fastapi-service.example.com
```

See [docs/deployment-managed-cloud.md](docs/deployment-managed-cloud.md) and [docs/vercel-backend-audit.md](docs/vercel-backend-audit.md).

## MCP

```powershell
cd mcp-server
npm install
$env:REPOGUARDIAN_API_URL="http://127.0.0.1:8000"
npm start
```

MCP exposes RHD tools, resources, and prompts. Write-gated actions remain human/policy gated. See [docs/mcp.md](docs/mcp.md).

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
npm run e2e
```

```powershell
cd mcp-server
npm run typecheck
npm test
```

## Safety

- Repository writes are allow-listed and require human approval.
- Public repositories are analyzed in read-only mode unless policy explicitly allows writes.
- Private repositories default to local/deterministic processing.
- Issue text, comments, README files, code, and PR descriptions are treated as untrusted evidence.
- Evidence must correspond to synchronized repository records.
- Frontend `NEXT_PUBLIC_` variables never contain backend secrets.
- Audit logs store safe summaries, not secrets or private reasoning.

## Current Limits

- Managed PostgreSQL/pgvector is ready for credentials but not connected in this local run.
- Redis is optional and not connected locally.
- Docker remains optional and unavailable on the current machine.
- `qwen3:1.7b` Ollama was validated locally; `qwen3:8b` was pulled but too slow for demo.
- ML/DL training is not claimed without a defensible labeled dataset.
- Production is not marked validated until deployed infrastructure and live production testing exist.

## Documentation

- [API](docs/api.md)
- [MCP](docs/mcp.md)
- [Managed Cloud Deployment](docs/deployment-managed-cloud.md)
- [Provider Benchmark](docs/provider-benchmark.md)
- [Industry Readiness](docs/industry-readiness-scorecard.md)
- [Public Source Audit](docs/public-source-audit.md)
