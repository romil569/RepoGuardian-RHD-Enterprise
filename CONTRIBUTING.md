# Contributing

Before opening a pull request:

1. Keep changes scoped.
2. Do not commit secrets, local databases, model binaries, or private datasets.
3. Run backend tests and frontend checks.
4. Keep external write actions human-gated.

Useful commands:

```powershell
cd backend
.\.venv\Scripts\python -m pytest

cd ..\frontend
npm run lint
npm run typecheck
npm run build

cd ..\mcp-server
npm run typecheck
npm test
```
