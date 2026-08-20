from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from app.core.config import settings
from app.db.models import Repository
from app.db.session import SessionLocal
from app.services.github_sync import sync_repository

logger = logging.getLogger(__name__)


class RepositorySyncScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if settings.repo_sync_interval_minutes <= 0 or self._task:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        interval = max(settings.repo_sync_interval_minutes, 5) * 60
        while True:
            await asyncio.sleep(interval)
            db = SessionLocal()
            try:
                for repo in db.query(Repository).all():
                    logger.info("scheduled repository sync started", extra={"repository": repo.full_name})
                    sync_repository(db, repo.id)
                    logger.info("scheduled repository sync completed", extra={"repository": repo.full_name})
            except Exception:
                logger.exception("scheduled repository sync failed")
            finally:
                db.close()


scheduler = RepositorySyncScheduler()
