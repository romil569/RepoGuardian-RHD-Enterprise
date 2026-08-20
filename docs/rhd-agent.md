# RHD Agent

RHD means Repository Health Director. RepoGuardian is the platform; RHD is the intelligence agent that performs repository analysis.

## Product Principle

RHD investigates.
RHD recommends.
Humans authorize external action.

## Repository Flow

Paste Repository -> RHD Syncs -> RHD Builds Context -> RHD Investigates -> RHD Validates Evidence -> RHD Prioritizes -> RHD Recommends -> Human Approves

RHD accepts either:

- `https://github.com/owner/repository`
- `owner/repository`

The configured demo repository can be write-enabled through the existing human approval and policy gate. Arbitrary public repositories are treated as read-only analysis targets.

## Controlled Intents

- `FULL_REPOSITORY_REVIEW`
- `HEALTH_EXPLANATION`
- `TOP_PRIORITIES`
- `ISSUE_LOOKUP`
- `DUPLICATE_ANALYSIS`
- `SECURITY_REVIEW`
- `RELEASE_ANALYSIS`
- `PR_ANALYSIS`
- `NEEDS_INFORMATION`
- `REPOSITORY_SEARCH`
- `MAINTAINER_BRIEF`
- `ACTION_RECOMMENDATION`
- `UNKNOWN`

Unknown or adversarial requests are refused when they ask RHD to fabricate evidence, ignore repository data, disclose secrets, or perform uncontrolled external action.

## Tool Orchestration

RHD routes questions to existing RepoGuardian capabilities:

- repository metadata
- repository health
- issue search
- project-aware RAG
- duplicate analysis
- issue completeness
- issue classification
- priority analysis
- security signals
- release regression
- related PR retrieval
- evidence retrieval
- review queue
- weekly brief
- audit context

Every response includes an operational RHD investigation trace. The trace lists tools and data categories used; it does not expose private reasoning.

## Deterministic Fallback

`OPENAI_API_KEY` is optional. Without it, RHD remains active through deterministic intent routing and structured response templates. The UI reports live language model status separately from RHD intelligence status.

## Source Grounding

Repository facts must come from synchronized repository data, repository analytics, indexed evidence, or verified issue/PR/release records. If there is insufficient evidence, RHD says so instead of guessing.

## Future Roadmap

Repository comparison can build on the same review schema by producing two repository-scoped RHD reviews and comparing health, backlog, response, security, and release stability.

Private repository support should use a GitHub App, organization installation, fine-grained permissions, RBAC, SSO, and tenant isolation. The current public repository onboarding path remains read-only outside the demo write allow-list.
