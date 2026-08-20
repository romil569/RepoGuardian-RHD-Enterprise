# API

Base URL is configured by the frontend with `NEXT_PUBLIC_API_URL`.

| Area | Endpoint | Purpose |
|---|---|---|
| Health | `GET /health` | Backend liveness |
| System | `GET /api/system/status` | Runtime/database/vector/provider status |
| Repositories | `POST /api/repositories/connect` | Connect a GitHub repository |
| Repositories | `POST /api/repositories/{id}/sync` | Sync repository evidence |
| Search | `POST /api/repositories/{id}/search` | Repository-scoped lexical/vector search |
| RHD | `POST /api/rhd/onboard` | Connect, sync, and run initial RHD review |
| RHD | `POST /api/rhd/query` | Ask RHD evidence-grounded questions |
| RAG v2 | `POST /api/platform/rag/query` | Agentic hybrid retrieval plan/evidence/critic |
| Tools | `GET /api/platform/tools` | Shared RHD tool registry |
| Tools | `POST /api/platform/tools/execute` | Execute read/analyze/recommend tools; write-gated tools require approval |
| Model Gateway | `GET /api/platform/model-gateway` | Provider status and circuit state |
| ML | `GET /api/platform/ml-models` | Honest model registry cards |
| Enterprise | `GET /api/platform/enterprise-readiness` | Managed cloud, Postgres, pgvector, queue readiness |
| Review Queue | `GET /api/review-queue` | Human-gated recommendations |
| Audit | `GET /api/audit-log` | Safe audit summaries |

OpenAPI remains available through FastAPI at `/docs` in environments where interactive docs are enabled.
