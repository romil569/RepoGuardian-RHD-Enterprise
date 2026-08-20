# GitHub Action Safety

Prompt 4 restricts GitHub writes through server-side policy and explicit maintainer approval.

## Safeguards

- Human approval is required by default.
- Writes are allow-listed to `romil569/RepoGuardian-Demo`.
- Label actions are limited to known safe labels.
- Comment actions validate length and sensitive-detail wording.
- Duplicate comments verify the target issue exists.
- Identical comments and repeated label actions are idempotent.
- Equivalent executed actions are blocked by an execution signature.
- Security-sensitive issues recommend security review and do not post detailed public exploit guidance.
- Failures are recorded as `FAILED` with a safe reason.

## Real Write Testing

Automated tests mock GitHub writes. Real validation should use at most one controlled write on `romil569/RepoGuardian-Demo`, and only after inspecting the action preview and approval record. If a real write is skipped to avoid repository noise, report `REAL_WRITE_TEST_SKIPPED`.

## Future Enterprise Safety

Future work should add GitHub App installation permissions, organization policy, RBAC, SSO, rate-limit dashboards, webhook verification, multi-tenant isolation, and enterprise audit retention.
