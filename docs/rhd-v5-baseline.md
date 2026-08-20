# RepoGuardian RHD v5 Baseline

Date: 2026-08-20

Baseline commit: `b6b3c7b`

Production release: `v2.0.0-rhd-intelligence`

Production URLs:

- Frontend: https://repoguardian-rhd.vercel.app
- Backend: https://repoguardian-rhd-api.vercel.app
- API docs: https://repoguardian-rhd-api.vercel.app/docs

Branch created for v5:

- `rhd-v5-chat-workspace`

Required pre-change validation:

- Backend tests: `71 passed`
- Frontend lint/typecheck/build: passed
- Frontend production build: `25` static routes
- MCP typecheck and smoke test: passed

v5 product direction:

- Replace dashboard-first home experience with a chat-first RHD workspace.
- Preserve all existing v4 intelligence, public read-only policy, deterministic fallback, and human-controlled external actions.
- Use a light, minimal, premium visual system.
- Add deterministic architecture artifacts based on actual repository evidence.
- Represent voice and multimodal support truthfully when no provider/browser capability is available.
