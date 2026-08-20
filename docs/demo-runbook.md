# RepoGuardian Final Demo Runbook

This deterministic 5-7 minute demo does not require Docker, pgvector, or a live LLM provider.

1. Open `http://127.0.0.1:3000`.
2. Overview: show GitHub-connected repository, health score, real issue counts, pending review, and system status.
3. Repositories: show `romil569/RepoGuardian-Demo`, sync status, and project-aware search.
4. Investigations: open issue `#3`, show missing information and `REQUEST_MORE_INFORMATION`.
5. Project-Aware RAG: open issue `#8` or `#6`, show duplicate/regression context and verified evidence.
6. Agentic Timeline: show the operational tool timeline and telemetry.
7. Selective Escalation: contrast documentation issue `#5` with security issue `#4`.
8. Security Case: show `HIGH_SECURITY_SIGNAL` and security review escalation.
9. Review Queue: show exact action preview and approval safeguard.
10. Audit Log: show traceability for recommendations, approvals/rejections, feedback, and actions.
11. Repository Health / Weekly Brief: show health dimensions and factual summary.
12. End with: "AI recommends; human controls external action."

Avoid real GitHub writes during judging unless a single controlled action has already been previewed and approved.

## Backup Steps

- If live GitHub briefly fails, use already synchronized local SQLite data.
- If OpenAI is not configured, point to system status: live AI provider not configured, deterministic intelligence active.
- If Docker is unavailable, explain the hackathon runtime uses SQLite/local vectors and production targets PostgreSQL/pgvector.
