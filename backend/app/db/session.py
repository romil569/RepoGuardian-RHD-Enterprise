from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args: dict[str, object] = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {"connect_timeout": 5}
engine_options: dict[str, object] = {"pool_pre_ping": True, "connect_args": connect_args}
if settings.database_url.startswith("sqlite"):
    pass
elif settings.postgres_runtime_mode == "managed":
    engine_options |= {
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout_seconds,
        "pool_recycle": settings.database_pool_recycle_seconds,
    }
else:
    engine_options["poolclass"] = NullPool
engine = create_engine(settings.sqlalchemy_database_url, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    if settings.is_serverless and not settings.enable_startup_schema_create:
        return
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
