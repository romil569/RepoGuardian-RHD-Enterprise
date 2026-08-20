from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.github_webhook import router as github_webhook_router
from app.api.routes.health import router as health_router
from app.api.routes.action_recommendations import router as action_recommendations_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.audit_log import router as audit_log_router
from app.api.routes.issues import router as issues_router
from app.api.routes.investigations import router as investigations_router
from app.api.routes.intelligence_v4 import router as intelligence_v4_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.platform import router as platform_router
from app.api.routes.repositories import router as repositories_router
from app.api.routes.rhd import router as rhd_router
from app.api.routes.settings import router as settings_router
from app.api.routes.system import router as system_router
from app.api.routes.workspace_v5 import router as workspace_v5_router
from app.core.config import settings
from app.db.session import initialize_database
from app.services.rate_limit import check_rate_limit
from app.services.scheduler import scheduler


_expensive_paths = ("/sync", "/onboard", "/query", "/investigate", "/rag/query")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.is_serverless or settings.enable_startup_schema_create:
        initialize_database()
    if not settings.is_serverless:
        scheduler.start()
    yield
    if not settings.is_serverless:
        await scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="RepoGuardian API", version="0.1.0", lifespan=lifespan)
    configured_origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list({settings.frontend_url, "http://127.0.0.1:3000", "http://localhost:3000", *configured_origins}),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def public_rate_limit(request: Request, call_next):
        if settings.public_analysis_mode:
            forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            client = forwarded_for or (request.client.host if request.client else "unknown")
            expensive = any(marker in request.url.path for marker in _expensive_paths)
            limit = settings.rate_limit_expensive_max_requests if expensive else settings.rate_limit_max_requests
            scope = "expensive" if expensive else "general"
            if not check_rate_limit(f"{client}:{scope}", scope, limit):
                return JSONResponse({"detail": "Rate limit reached. Please wait before running more repository analysis."}, status_code=429)
        return await call_next(request)

    app.include_router(health_router)
    app.include_router(system_router, prefix="/api/system", tags=["system"])
    app.include_router(repositories_router)
    app.include_router(rhd_router)
    app.include_router(platform_router)
    app.include_router(issues_router)
    app.include_router(investigations_router)
    app.include_router(intelligence_v4_router)
    app.include_router(workspace_v5_router)
    app.include_router(jobs_router)
    app.include_router(analytics_router)
    app.include_router(action_recommendations_router)
    app.include_router(audit_log_router)
    app.include_router(settings_router)
    app.include_router(github_webhook_router)

    return app


app = create_app()
