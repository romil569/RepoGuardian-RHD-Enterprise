# Webhooks

Endpoint:

- `POST /api/github/webhooks`
- compatibility alias: `POST /api/github/webhook`

If `GITHUB_WEBHOOK_SECRET` is configured, the endpoint verifies `X-Hub-Signature-256`.

Supported event families:

- `issues`
- `issue_comment`
- `pull_request`
- `pull_request_review`
- `push`
- `release`

Flow:

GitHub Event -> Signature Verification -> Normalize Event -> Store RepositoryEvent -> Queue Job -> RHD Processing

Current job mappings:

- issues -> issue investigation
- issue comments -> issue investigation
- pull requests -> PR risk analysis
- pull request reviews -> PR risk analysis
- push -> code index
- release -> release analysis

Unknown repositories are accepted but not stored until the repository is connected. This avoids creating unverified tenant records.
