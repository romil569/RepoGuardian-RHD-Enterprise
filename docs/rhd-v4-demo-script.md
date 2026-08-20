# RepoGuardian RHD v4 Demo Script

## 1. Mission Control

Open `/mission-control`.

Show that RepoGuardian is powered by RHD and operating in public read-only mode. Point out repository, issue, PR, capability, and human-control status.

## 2. Agent Mesh

Call `GET /api/v4/agent-mesh` or inspect Mission Control capabilities.

Highlight the specialist agents and governance rules:

- Evidence required
- Private repository AI restrictions
- Human approval for external actions
- Repository content treated as untrusted input

## 3. Intelligence Map

Open `/intelligence-map`.

Explain that graph and code-symbol rows are repository-scoped. If no code index exists for the selected repository, the UI truthfully reports that the map is awaiting graph or code-index data.

## 4. Pull Request Intelligence

Open `/pull-requests`.

Use `GET /api/v4/pr/{repository_id}/{pr_number}/risk` and `/blast-radius` when synced PR data exists. Emphasize that RepoGuardian uses synced PR metadata and code symbols only; it does not fabricate changed files or reviewers.

## 5. Incident Intelligence

Open `/incidents`.

Run `POST /api/v4/incidents/investigate` with a repository id and query such as `login regression after auth release`. The response includes evidence, timeline rows, cautious hypotheses, and an evidence critic.

## 6. Code Intelligence

Open `/code-intelligence`.

Show bounded code-symbol and Code-RAG readiness. In serverless cloud mode local filesystem scanning stays disabled for safety.

## 7. Models Lab

Open `/models` and call `GET /api/v4/models/lab`.

Explain the model gateway tasks and ML cards. RepoGuardian does not claim custom-trained ML metrics without actual training and validation data.

## 8. Observatory

Open `/observatory`.

Show audit, conversation, model telemetry, PR risk, and incident counters. These are operational traces, not private chain-of-thought.

## 9. Human Control

Open `/review-queue`.

Approve/reject paths remain explicit. Public production keeps `GITHUB_WRITE_MODE=disabled`, so anonymous users cannot execute external writes.
