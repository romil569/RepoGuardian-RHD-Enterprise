# GitHub App Setup

Local development continues to support GitHub CLI authentication.

Production GitHub App support is configured through:

- `GITHUB_AUTH_MODE=app`
- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY_PATH`
- `GITHUB_APP_INSTALLATION_ID`
- `GITHUB_WEBHOOK_SECRET`

Manual setup steps:

1. Create a GitHub App in the target organization or user account.
2. Grant least-privilege permissions for repository metadata, issues, pull requests, contents read, and webhooks.
3. Enable write permissions only for actions intentionally supported by RepoGuardian policy.
4. Generate a private key and store it in a secret manager or protected filesystem path.
5. Configure webhook URL: `/api/github/webhooks`.
6. Configure webhook secret and set `GITHUB_WEBHOOK_SECRET`.
7. Install the app on selected repositories.

Never expose the private key or installation token to the frontend.
