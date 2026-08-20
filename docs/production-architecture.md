# Production Architecture

Target architecture:

GitHub App
-> GitHub Webhooks
-> Event Gateway
-> Queue
-> Sync / Code / AI-ML Workers
-> Repository Intelligence Layer
-> SQL + Vector + Graph
-> Graph-RAG / Code-RAG
-> RHD Supervisor
-> Specialist Agents
-> ML Intelligence
-> Evidence Critic
-> Policy Engine
-> Human Control
-> Safe GitHub Actions

Implemented and locally validated:

- local development fallback
- model gateway abstraction
- local queue abstraction
- graph store abstraction with local backend
- webhook signature verification and event normalization
- code intelligence foundation
- ML model registry with honest status values
- production compose skeleton
- Terraform AWS skeleton syntax validation
- Playwright responsive UI tests

Production dependencies remain optional for local demo:

- PostgreSQL + pgvector
- Redis
- GitHub App
- cloud or local model provider
- container platform

## Actual Activation Status

| Capability | Status | Notes |
|---|---|---|
| SQLite/local vectors | LOCALLY_VALIDATED | Lightweight demo path remains stable |
| PostgreSQL | DEPLOYMENT_READY | Compose configured; live validation blocked until Docker Desktop exists |
| pgvector | DEPLOYMENT_READY | Compose uses `pgvector/pgvector:pg16`; extension not live-validated |
| Redis | DEPLOYMENT_READY | Compose configured; live queue validation blocked until Docker Desktop exists |
| Worker | PARTIAL | Script and image exist; production worker consumption needs Redis activation |
| Terraform | LOCALLY_VALIDATED | `fmt`, `init -backend=false`, and `validate` passed; no apply run |
| GitHub App | NOT_CONFIGURED | Setup docs exist; account-owner action required |
| Webhooks | LOCALLY_VALIDATED | Signature and event tests pass; no public tunnel/live GitHub delivery configured |
| Ollama | LOCALLY_VALIDATED | `qwen3:1.7b` generated through local API and gateway; `qwen3:8b` pulled but too slow for demo |
| Playwright | LOCALLY_VALIDATED | 24 route/viewport checks pass |

No production infrastructure has been provisioned.
