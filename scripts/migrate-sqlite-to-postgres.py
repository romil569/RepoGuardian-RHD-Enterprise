#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, JSON, create_engine, func, insert, select, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.base import Base  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely migrate RepoGuardian SQLite rows into PostgreSQL.")
    parser.add_argument("--sqlite", required=True, help="Source SQLite database path.")
    parser.add_argument("--postgres-url", required=True, help="Destination postgresql+psycopg SQLAlchemy URL.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and copy inside a transaction that is rolled back.")
    parser.add_argument("--verify-only", action="store_true", help="Only compare source/destination row counts.")
    return parser.parse_args()


def source_engine(path: str) -> Engine:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"SQLite source does not exist: {source}")
    return create_engine(f"sqlite:///{source}")


def destination_engine(url: str) -> Engine:
    if not url.startswith("postgresql"):
        raise SystemExit("Destination must be a PostgreSQL SQLAlchemy URL.")
    return create_engine(url, pool_pre_ping=True)


def coerce_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, JSON) and isinstance(value, str):
        return json.loads(value)
    if isinstance(column.type, DateTime) and isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return value


def read_rows(engine: Engine, table: Any) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        result = connection.execute(select(table)).mappings()
        return [{column.name: coerce_value(column, row[column.name]) for column in table.columns} for row in result]


def table_counts(engine: Engine) -> dict[str, int]:
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            counts[table.name] = int(connection.execute(select(func.count()).select_from(table)).scalar_one())
    return counts


def validate_destination(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        dialect = connection.dialect.name
        if dialect != "postgresql":
            raise SystemExit(f"Destination dialect must be postgresql, got {dialect}")
        existing = set(connection.execute(text("select tablename from pg_tables where schemaname = 'public'")).scalars())
    missing = [table.name for table in Base.metadata.sorted_tables if table.name not in existing]
    if missing:
        raise SystemExit(f"Destination is missing migrated tables. Run Alembic migrations first: {', '.join(missing)}")


def verify_counts(source: Engine, destination: Engine) -> dict[str, dict[str, int | bool]]:
    source_counts = table_counts(source)
    dest_counts = table_counts(destination)
    return {
        name: {"source": source_counts[name], "destination": dest_counts.get(name, 0), "match": source_counts[name] == dest_counts.get(name, 0)}
        for name in source_counts
    }


def migrate(source: Engine, destination: Engine, dry_run: bool) -> dict[str, int]:
    inserted: dict[str, int] = {}
    with destination.connect() as connection:
        transaction = connection.begin()
        try:
            for table in Base.metadata.sorted_tables:
                rows = read_rows(source, table)
                inserted[table.name] = len(rows)
                if rows:
                    connection.execute(insert(table), rows)
            if dry_run:
                transaction.rollback()
            else:
                transaction.commit()
        except Exception:
            transaction.rollback()
            raise
    return inserted


def main() -> None:
    args = parse_args()
    source = source_engine(args.sqlite)
    destination = destination_engine(args.postgres_url)
    validate_destination(destination)

    if args.verify_only:
        print(json.dumps({"mode": "verify-only", "counts": verify_counts(source, destination)}, indent=2, default=str))
        return

    inserted = migrate(source, destination, dry_run=args.dry_run)
    verification = verify_counts(source, destination) if not args.dry_run else {}
    print(json.dumps({"mode": "dry-run" if args.dry_run else "migrated", "inserted": inserted, "verification": verification}, indent=2, default=str))


if __name__ == "__main__":
    main()
