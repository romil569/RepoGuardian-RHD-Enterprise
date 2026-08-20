from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.github_webhook import router as github_webhook_router
from app.api.routes.health import router as health_router
from app.api.routes.action_recommendations import router as action_recommendations_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.audit_log import router as audit_log_router
from app.api.routes.issues import router as issues_router
from app.api.routes.investigations import router as investigations_router
from app.api.routes.platform import router as platform_router
from app.api.routes.repositories import router as repositories_router
from app.api.routes.rhd import router as rhd_router
from app.api.routes.settings import router as settings_router
from app.api.routes.system import router as system_router
from app.core.config import settings
from app.db.session import initialize_database
from app.services.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    scheduler.start()
    yield
    await scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="RepoGuardian API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list({settings.frontend_url, "http://127.0.0.1:3000", "http://localhost:3000"}),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(system_router, prefix="/api/system", tags=["system"])
    app.include_router(repositories_router)
    app.include_router(rhd_router)
    app.include_router(platform_router)
    app.include_router(issues_router)
    app.include_router(investigations_router)
    app.include_router(analytics_router)
    app.include_router(action_recommendations_router)
    app.include_router(audit_log_router)
    app.include_router(settings_router)
    app.include_router(github_webhook_router)

    return app


app = create_app()
