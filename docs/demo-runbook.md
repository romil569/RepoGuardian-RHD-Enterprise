# RepoGuardian Final Demo Runbook

This deterministic 5-7 minute demo does not require Docker, pgvector, or a live LLM provider.

1. Open `http://127.0.0.1:3000`.
2. Say: "Instead of manually searching through hundreds of issues and PRs, a maintainer gives RHD a GitHub repository and asks for a review."
3. Paste `https://github.com/romil569/RepoGuardian-Demo` into the RHD repository input.
4. Show RHD Initial Scan and the RHD Full Repository Review.
5. Ask RHD: "What should I fix first?"
6. Show Today's Maintainer Priorities and cited issue evidence.
7. Ask RHD: "Show duplicate issues."
8. Ask RHD: "Which issues are security-sensitive?"
9. Ask RHD: "What happened after v1.2.0?"
10. Open Investigations and show issue-level evidence, duplicate/security/release analysis, and operational trace.
11. Open Review Queue and show exact action preview and approval safeguard.
12. Open Audit Log and show traceability for recommendations, approvals/rejections, RHD queries, feedback, and actions.
13. End with: "RHD investigates and recommends. Humans remain in control of external actions."

Avoid real GitHub writes during judging unless a single controlled action has already been previewed and approved.

## Backup Steps

- If live GitHub briefly fails, use already synchronized local SQLite data.
- If OpenAI is not configured, point to system status: live AI provider not configured, deterministic intelligence active.
- If Docker is unavailable, explain the hackathon runtime uses SQLite/local vectors and production targets PostgreSQL/pgvector.
