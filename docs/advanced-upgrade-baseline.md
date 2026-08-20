# Advanced Upgrade Baseline

Date: 2026-08-20

## Stable Checkpoints

- Current stable RHD release: `2915116`
- Current stable tag: `hackathon-demo-v3-rhd`
- Previous stable UI: `c8e0f99`
- Previous production-demo baseline: `74075da`

## Repository State

- `git status --short`: clean
- `git log --oneline -10`: verified current RHD commit and previous prompt checkpoints
- `git tag`: verified `hackathon-demo-v1`, `hackathon-demo-v2-ui`, and `hackathon-demo-v3-rhd`

## Inspected Areas

- `AGENTS.md`
- `README.md`
- `docs/`
- `backend/`
- `frontend/`
- `scripts/`
- `infrastructure/`

## Regression Commands

| Area | Command | Status |
|---|---|---|
| Backend | `backend\.venv\Scripts\pytest.exe -q` | PASS, 37 passed |
| Frontend lint | `npm run lint` | PASS |
| Frontend typecheck | `npm run typecheck` | PASS |
| Frontend build | `npm run build` | PASS |

## Runtime Verification

- Frontend `http://127.0.0.1:3000/`: HTTP 200
- Backend `http://127.0.0.1:8000/health`: HTTP 200

## Browser QA

Checked routes:

- Command Center `/`
- Repositories `/repositories`
- Investigations `/investigations`
- Review Queue `/review-queue`
- Health `/health`
- Weekly Brief `/weekly`
- Audit Log `/audit-log`
- Settings `/settings`

Result:

- RHD branding visible
- No horizontal overflow detected
- No browser console errors detected
- RHD query endpoint returned grounded responses with traces and sources for:
  - `Give me a full review.`
  - `What should I fix first?`
  - `Show duplicate issues.`

## Baseline Conclusion

The `hackathon-demo-v3-rhd` baseline is healthy and recoverable. Advanced platform work can proceed incrementally without modifying or deleting the stable tag.
