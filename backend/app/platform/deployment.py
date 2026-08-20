from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.config import settings


class ComponentStatus(StrEnum):
    VALIDATED = "VALIDATED"
    IMPLEMENTED = "IMPLEMENTED"
    PARTIAL = "PARTIAL"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    ROADMAP = "ROADMAP"


@dataclass(frozen=True)
class RuntimeCheck:
    component: str
    status: ComponentStatus
    detail: str


def deployment_profile() -> dict[str, object]:
    return {
        "active_mode": settings.deployment_mode,
        "supported_modes": ["LIGHTWEIGHT_LOCAL", "INDUSTRY_LOCAL", "MANAGED_CLOUD", "ENTERPRISE_AWS"],
        "managed_cloud": {
            "frontend": "Vercel-compatible Next.js",
            "backend": "Vercel Python serverless FastAPI",
            "database": "Neon PostgreSQL with pgvector",
            "queue": "Postgres serverless job queue, local development fallback",
            "model_gateway": "Deterministic fallback, optional cloud providers, local Ollama development only",
        },
    }


def database_runtime_checks(engine: Engine) -> list[RuntimeCheck]:
    checks: list[RuntimeCheck] = []
    url = settings.database_url
    is_postgres = url.startswith(("postgresql://", "postgresql+"))
    if not is_postgres:
        checks.append(RuntimeCheck("postgres", ComponentStatus.NOT_CONFIGURED, "DATABASE_URL is not PostgreSQL"))
        checks.append(RuntimeCheck("pgvector", ComponentStatus.NOT_CONFIGURED, "Local vector fallback is active"))
        return checks

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks.append(RuntimeCheck("postgres", ComponentStatus.VALIDATED, "Connection succeeded"))
    except Exception as exc:
        checks.append(RuntimeCheck("postgres", ComponentStatus.PARTIAL, f"Connection failed: {exc}"))
        checks.append(RuntimeCheck("pgvector", ComponentStatus.NOT_CONFIGURED, "Skipped because PostgreSQL connection failed"))
        return checks

    checks.append(_pgvector_check(engine))
    return checks


def _pgvector_check(engine: Engine) -> RuntimeCheck:
    try:
        with engine.begin() as connection:
            installed = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
            if installed:
                return RuntimeCheck("pgvector", ComponentStatus.VALIDATED, "Extension already installed")
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                installed_after_create = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
            except Exception as exc:
                return RuntimeCheck("pgvector", ComponentStatus.PARTIAL, f"Extension unavailable and CREATE EXTENSION failed safely: {exc}")
    except Exception as exc:
        return RuntimeCheck("pgvector", ComponentStatus.PARTIAL, f"Extension check failed safely: {exc}")

    if installed_after_create:
        return RuntimeCheck("pgvector", ComponentStatus.VALIDATED, "Extension created or confirmed")
    return RuntimeCheck("pgvector", ComponentStatus.PARTIAL, "Extension not present after non-destructive check")


def queue_runtime_check() -> RuntimeCheck:
    if settings.queue_backend == "redis":
        if settings.redis_url:
            return RuntimeCheck("queue", ComponentStatus.IMPLEMENTED, "Redis queue selected; live connection is validated by worker startup")
        return RuntimeCheck("queue", ComponentStatus.NOT_CONFIGURED, "Redis queue selected but REDIS_URL is not set")
    if settings.queue_backend == "postgres":
        if settings.database_url.startswith(("postgresql://", "postgresql+")):
            return RuntimeCheck("queue", ComponentStatus.IMPLEMENTED, "Postgres queue fallback selected")
        return RuntimeCheck("queue", ComponentStatus.PARTIAL, "Postgres queue selected without PostgreSQL DATABASE_URL")
    return RuntimeCheck("queue", ComponentStatus.VALIDATED, "Local in-process queue selected")


def enterprise_readiness(engine: Engine) -> dict[str, object]:
    checks = [*database_runtime_checks(engine), queue_runtime_check()]
    return {
        "profile": deployment_profile(),
        "checks": [check.__dict__ | {"status": check.status.value} for check in checks],
    }
