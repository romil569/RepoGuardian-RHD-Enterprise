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

## Backend API

New read-only endpoints:

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
