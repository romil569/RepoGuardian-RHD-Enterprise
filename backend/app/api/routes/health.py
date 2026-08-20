from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "RepoGuardian"}


@router.get("/readiness")
def readiness() -> dict[str, object]:
    checks: dict[str, str] = {"application": "ok"}
    status = "ready"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        status = "degraded"
    return {"status": status, "checks": checks}
