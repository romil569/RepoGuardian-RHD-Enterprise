# Public Source Audit

Status: `PENDING_FINAL_SCAN`.

Before pushing to `romil569/RepoGuardian-RHD-Enterprise`, run:

```powershell
git diff --check
git status --short
rg -n --hidden --glob '!frontend/node_modules/**' --glob '!mcp-server/node_modules/**' --glob '!backend/.venv/**' "API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE KEY|DATABASE_URL=.*://|github_pat|ghp_"
rg --files --hidden | rg "\.env$|\.db$|\.sqlite|node_modules|\.venv|Ollama|model|cache|\.log$"
```

Rules:

- `.env` and `.env.*` stay ignored except checked-in examples.
- SQLite databases are ignored.
- `node_modules`, virtualenvs, model binaries, caches, logs, and Terraform working directories are ignored.
- Do not push credentials, private keys, local databases, model weights, or private datasets.
