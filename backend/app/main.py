from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.system import router as system_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="RepoGuardian API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(system_router, prefix="/api/system", tags=["system"])
    return app


app = create_app()
