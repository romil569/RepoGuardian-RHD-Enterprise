# RepoGuardian Security Notes

## Repository Allow-List

Automated write execution is server-side allow-listed. The default allowed write repository is `romil569/RepoGuardian-Demo`. Non-allow-listed repositories are blocked even if a frontend caller manually invokes the execute endpoint.

## Repository Isolation

Repository-scoped retrieval filters on `repository_id` before ranking evidence. Tests cover cross-repository isolation.

## Evidence Validation

Investigation evidence is validated against synchronized repository records. Fabricated issue IDs, PRs, release references, unknown source types, and cross-repository references are rejected.

## Human Approval

External GitHub actions require explicit maintainer approval by default. The current hackathon actor is `local-maintainer`, not production RBAC.

## Secret Handling

Secrets are loaded server-side only. System status reports only configured/not-configured state for OpenAI and never returns the key. `.env` files are ignored by Git. Audit metadata redacts sensitive-looking keys.

## Prompt and Tool Safety

Repository content, issue text, comments, release notes, and code are treated as untrusted input. RHD must ground recommendations in synchronized evidence, keep deterministic fallback available, and avoid executing repository code during static analysis.

## Private Repository Policy

The model gateway skips external cloud providers for private repository context unless `ALLOW_EXTERNAL_MODEL_FOR_PRIVATE_REPOS=true` is explicitly configured. Deterministic fallback remains available for private repositories without sending code or issue text to a cloud model.

## AI Uncertainty

Confidence is an internal decision signal, not a guarantee. Deterministic fallback remains active when OpenAI is unavailable. The system avoids fabricated evidence and keeps controlled enums for classifications, priorities, and escalations.

## Security-Sensitive Issues

High security signals recommend human/security review. RepoGuardian does not automatically request public exploit details, passwords, API keys, tokens, or private credentials.

## GitHub Write Restrictions

Supported write actions are limited to safe labels and safe comments after approval and policy validation. RepoGuardian does not close issues, merge PRs, delete branches, delete issues, or publish security disclosure details.

## Audit Logging

Audit logs record syncs, investigations, recommendations, approvals, rejections, policy blocks, feedback, and execution results using safe summaries.

## Current Limitations

- GitHub App identity is configured as a target mode but not connected to a real installation in this workspace.
- Production RBAC/SSO is not implemented.
- Docker/PostgreSQL/pgvector validation depends on Docker availability.
- Live external provider validation requires configuring provider credentials or a reachable Ollama runtime.
