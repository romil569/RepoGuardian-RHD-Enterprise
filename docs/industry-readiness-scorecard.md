# Industry Readiness Scorecard

Status labels are evidence-based:

- `DEMO_READY`: works for the current deterministic/local demo.
- `PRODUCTION_FOUNDATION`: architecture and code foundations exist but are not fully provisioned.
- `PRODUCTION_VALIDATED`: validated against production-like infrastructure.
- `BLOCKED`: requires missing local tool, credential, account action, or paid infrastructure authorization.

| Area | Status | Evidence |
|---|---|---|
| AI Intelligence | DEMO_READY | RHD deterministic answers, evidence guardrails, provider gateway fallback tests, local Ollama probe |
| ML Maturity | PRODUCTION_FOUNDATION | Model registry and dataset strategy exist; no models trained without defensible data |
| Data Layer | DEMO_READY | SQLite/local vectors validated; PostgreSQL/pgvector blocked by missing Docker |
| Agent Reliability | DEMO_READY | RHD tests, action recommendation policy, audit flow |
| Security | DEMO_READY | Evidence validation, human approval, private provider policy, webhook signature tests |
| GitHub Integration | DEMO_READY | GitHub CLI available; GitHub App not configured |
| Observability | PRODUCTION_FOUNDATION | Audit/telemetry available; OpenTelemetry/metrics endpoint not yet activated |
| Deployment | PRODUCTION_FOUNDATION | Docker/Compose/Terraform assets exist; Terraform validated; Docker not installed |
| Automation | PRODUCTION_FOUNDATION | Webhook endpoint and local queue exist; production webhooks/worker blocked by Docker/GitHub App setup |
| Human Governance | DEMO_READY | Review queue, policy gate, safe write allow-list, audit trail |

## Overall Readiness

| Mode | Status | Reason |
|---|---|---|
| Lightweight Hackathon | READY | SQLite, local vectors, deterministic intelligence, UI, RHD flows, and tests pass |
| Industry Local | PARTIAL | Terraform, Playwright, and local Ollama activated; Docker/PostgreSQL/Redis still blocked |
| Staging | PARTIAL | Containers/IaC/config/docs exist; needs Docker validation and external service credentials |
| Production | NOT_READY | No cloud provisioning, GitHub App, managed database, Redis, or production provider validation |
