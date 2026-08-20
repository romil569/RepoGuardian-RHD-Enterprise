# RepoGuardian RHD v5 Chat Workspace

RHD v5 changes RepoGuardian from a dashboard-first product into a chat-first repository intelligence workspace.

## Product Experience

The home route `/` now opens directly into:

- Left conversation/repository/tool sidebar on desktop
- Main RHD conversation
- Bottom composer with repository detection, attachment, repository, voice, provider, stop/send controls
- Right context panel with tabs for Context, Architecture, Code, Evidence, Agents, and Activity
- Mobile-first chat surface with side panels removed from the main flow

Existing dashboards remain available as assistant-accessible tools and pages. The v5 workspace does not remove v4 intelligence.

## v5.1 End-To-End Flow

The public home route supports the complete repository journey:

1. Paste `https://github.com/owner/repository`, `github.com/owner/repository`, or `owner/repository`.
2. `POST /api/v5/repositories/analyze` creates a persisted `DeploymentJob`.
3. The frontend polls `GET /api/v5/jobs/{job_id}`; each poll advances one bounded serverless-safe stage.
4. RHD syncs repository metadata, issues, pull requests, releases, selected source files, code symbols, indexed evidence, review output, and persisted architecture artifacts.
5. Completion appears inline in chat with an SVG architecture card and populated context tabs.
6. Reloading the workspace restores the latest persisted repository architecture context.
7. Follow-up questions use the selected repository/session context; public repositories remain read-only.

## Backend API

New read-only endpoints:

- `POST /api/v5/repositories/analyze`
- `GET /api/v5/jobs/{job_id}`
- `GET /api/v5/workspace`
- `GET /api/v5/conversations`
- `GET /api/v5/repositories/{repository_id}/architecture`
- `GET /api/v5/capabilities`

Conversation history uses the existing `public_sessions` and `conversation_messages` tables.

## Architecture Artifacts

Architecture diagrams are generated deterministically from synchronized repository evidence:

- repository metadata
- indexed documents
- issues
- pull requests
- releases
- code-symbol rows when available
- RHD repository review output

Each artifact includes:

- Mermaid source
- SVG output
- grounding explanation
- export actions

The system does not fabricate module relationships. If code evidence is weak, artifacts are marked `METADATA_ONLY`.

## Multimodal And Voice

Voice controls are optional browser-level UI affordances.

Direct image understanding is reported as `PROVIDER_REQUIRED` unless a multimodal provider is actually configured. RepoGuardian does not fake screenshot or diagram understanding.

## Safety

- Public users remain read-only.
- External GitHub action remains human-gated.
- Deterministic fallback remains active.
- Repository content is untrusted input.
- Token usage is not fabricated; deterministic execution reports `N/A`.
