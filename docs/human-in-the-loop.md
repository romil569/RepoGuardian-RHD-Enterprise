# Human-In-The-Loop Workflow

RepoGuardian Prompt 4 turns intelligence results into reviewable maintainer actions. Investigations can recommend actions, but they do not execute external writes.

## Workflow

1. Investigation completes.
2. RepoGuardian creates an `ActionRecommendation`.
3. The recommendation appears in the Review Queue as `PENDING`.
4. A local hackathon maintainer identity, currently `local-maintainer`, approves or rejects.
5. Execution is allowed only after approval.
6. Server-side policy validates the action again.
7. The GitHub action executes or is blocked.
8. Audit events record the outcome.

## Supported Actions

- `NO_ACTION`
- `ADD_LABEL`
- `POST_COMMENT`
- `REQUEST_MORE_INFORMATION`
- `MARK_AS_POSSIBLE_DUPLICATE`
- `ESCALATE_FOR_MAINTAINER_REVIEW`
- `ESCALATE_FOR_SECURITY_REVIEW`

RepoGuardian does not automatically close issues, merge PRs, delete branches, delete issues, or publish security disclosure details.

## Reviewer Identity

The current hackathon build uses `local-maintainer`. This is not production RBAC. Future enterprise versions should use GitHub OAuth or GitHub App identity, organization membership checks, RBAC, SSO, and audit retention policies.
