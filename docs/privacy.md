# Privacy

Repository privacy mode governs provider routing.

Modes:

- `PUBLIC`
- `PRIVATE_LOCAL_AI_ONLY`
- `PRIVATE_EXTERNAL_AI_ALLOWED`

Current default:

Private repository content should use local or deterministic processing unless `ALLOW_EXTERNAL_MODEL_FOR_PRIVATE_REPOS=true`.

Public repositories may use configured cloud providers, but evidence must still pass repository validation.

Never send:

- API keys
- tokens
- webhook secrets
- GitHub App private keys
- browser cookies
- local credentials

Security-sensitive issue handling must avoid asking reporters to post secrets or exploit details publicly.
