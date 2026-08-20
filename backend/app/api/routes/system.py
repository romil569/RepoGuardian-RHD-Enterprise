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

    live_ai_configured = bool(settings.openai_api_key)
    ai_provider = "not_configured"
    deterministic_active = True
    if settings.ai_provider_mode == "openai":
        ai_provider = "configured" if live_ai_configured else "not_configured"
        deterministic_active = not live_ai_configured
    elif settings.ai_provider_mode == "auto":
        ai_provider = "configured" if live_ai_configured else "not_configured"

    return {
        "backend": "ok",
        "database": database,
        "app_env": settings.app_env,
        "demo_repository": settings.demo_github_repository,
        "data_backend": settings.data_backend,
        "vector_backend": settings.vector_backend,
        "ai_provider": ai_provider,
        "ai_provider_mode": settings.ai_provider_mode,
        "live_ai_provider": "connected" if live_ai_configured else "not_configured",
        "deterministic_intelligence": "active" if deterministic_active else "fallback_available",
    }
