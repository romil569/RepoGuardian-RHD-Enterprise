# RepoGuardian RHD v5 E2E Gap Analysis

Baseline: `279635b` / `v3.0.0-rhd-conversational`

Prompt test repository: `https://github.com/romil569/RepoGuardian-Demo`

## Current Flow Before v5.1

1. User opens `https://repoguardian-rhd.vercel.app`.
2. Homepage renders the RHD chat workspace.
3. Composer detects only `https://github.com/owner/repository` and `owner/repository`.
4. `github.com/owner/repository` without protocol is not detected.
5. Pressing Send with a repository calls the older `/api/rhd/onboard` flow.
6. In serverless mode `/api/rhd/onboard` creates a persisted `DeploymentJob`.
7. Frontend advances the job through `/api/jobs/{id}/advance`.
8. The existing job stages sync issues, PRs, releases, indexed evidence, health, and review.
9. Source tree/code architecture is not part of the persisted job stages.
10. Architecture artifacts are generated on demand by `/api/v5/repositories/{repository_id}/architecture`, not as a required analysis stage.
11. Architecture artifacts are not persisted in a dedicated artifact table.
12. The welcome suggestion chips set text but do not all produce useful results before a repository is selected.
13. There is no single v5 analysis API contract for start/status.

## Broken Or Disconnected Steps

| Step | Finding | Fix |
|---|---|---|
| Repository detection | `github.com/owner/repository` not accepted | Extend parser in frontend and backend |
| Start analysis | Homepage uses older onboarding route | Add `POST /api/v5/repositories/analyze` |
| Job polling | Homepage polls legacy route and separate advance route | Add `GET /api/v5/jobs/{job_id}` that advances one persisted stage per poll |
| Source analysis | Existing sync indexes issues/PRs/releases only | Add bounded GitHub tree/source scan stage |
| Symbols | Code symbols only from local scanning path | Add serverless GitHub source-file symbol extraction |
| Architecture | Generated on demand, not persisted as job result | Persist `ArchitectureArtifact` rows |
| Completion chat | Review message is generic | Show health, architecture status, code files/symbols, issue/PR counts |
| Context panel | Can remain sparse until manual architecture fetch | Populate from completed job payload |
| Demo button | No real one-click demo analysis | Add Try Demo Repository button using real backend workflow |

## v5.1 Integration Target

The fixed flow is:

`Paste repository -> POST /api/v5/repositories/analyze -> persisted DeploymentJob -> frontend GET /api/v5/jobs/{id} polling -> staged sync/source/architecture/review -> inline chat completion + SVG architecture + populated context panel -> follow-up questions use current repository context`.
