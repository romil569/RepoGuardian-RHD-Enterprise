# RepoGuardian Prompt 4 Demo Runbook

This deterministic 5-7 minute demo does not require Docker, pgvector, or a live LLM provider.

1. Open `http://127.0.0.1:3000`.
2. Show the Overview dashboard with repository health, pending actions, and recent audit events.
3. Open Repositories and show `romil569/RepoGuardian-Demo`.
4. Open Repository Health and show score, dimensions, weekly brief, and evaluation status.
5. Open Investigations and run or show Issue `#3` style incomplete issue.
6. Point out missing information and the `REQUEST_MORE_INFORMATION` recommendation.
7. Open Review Queue and show the exact proposed comment preview.
8. Explain that approval is required and execution is policy-validated server-side.
9. Open Audit Log and show recommendation creation, approval, rejection, or execution events.
10. Open a duplicate issue investigation such as `#1` or `#6` and show verified historical evidence.
11. Open security issue `#4` and show `HIGH_SECURITY_SIGNAL` / security review escalation.
12. Return to Weekly Brief for the executive summary.
13. End with the roadmap: GitHub App identity, organization membership, RBAC, SSO, enterprise policy engine, multi-tenant isolation, and audit retention.

Avoid real GitHub writes during judging unless a single controlled action has already been previewed and approved.
