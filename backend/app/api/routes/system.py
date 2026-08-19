from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter()


@router.get("/status")
def system_status() -> dict[str, object]:
    database = "unavailable"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"

    return {
        "backend": "ok",
        "database": database,
        "app_env": settings.app_env,
        "demo_repository": settings.demo_github_repository,
    }
