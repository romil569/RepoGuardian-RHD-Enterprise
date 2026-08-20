# Database Migration Report

Status: `MANAGED_POSTGRES_READY_NOT_CONNECTED`.

The SQLite to PostgreSQL utility exists at:

```powershell
scripts\migrate-sqlite-to-postgres.py
```

Validated locally:

- rejects non-PostgreSQL destination URLs
- supports dry-run behavior
- preserves the SQLite source
- verifies table row counts

Live managed PostgreSQL migration was not run because no managed database credentials were provided.

Recommended command when credentials exist:

```powershell
python scripts\migrate-sqlite-to-postgres.py --source backend\repoguardian-dev.db --destination $env:DATABASE_URL --dry-run --verify
```

Run without `--dry-run` only after reviewing the dry-run report.
