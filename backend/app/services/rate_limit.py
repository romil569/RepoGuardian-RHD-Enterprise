from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from time import monotonic

from sqlalchemy import delete

from app.core.config import settings
from app.db.models import PublicRateLimitEvent
from app.db.session import SessionLocal

_local_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, scope: str, limit: int) -> bool:
    if settings.queue_backend == "postgres" and settings.database_url.startswith(("postgresql://", "postgresql+")):
        return _check_postgres_rate_limit(key, scope, limit)
    return _check_local_rate_limit(key, limit)


def _check_local_rate_limit(key: str, limit: int) -> bool:
    now = monotonic()
    bucket = _local_rate_buckets[key]
    while bucket and now - bucket[0] > settings.rate_limit_window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def _check_postgres_rate_limit(key: str, scope: str, limit: int) -> bool:
    db = SessionLocal()
    try:
        window_start = datetime.now(UTC) - timedelta(seconds=settings.rate_limit_window_seconds)
        db.execute(delete(PublicRateLimitEvent).where(PublicRateLimitEvent.created_at < window_start))
        count = db.query(PublicRateLimitEvent).filter_by(key=key, scope=scope).filter(PublicRateLimitEvent.created_at >= window_start).count()
        if count >= limit:
            db.commit()
            return False
        db.add(PublicRateLimitEvent(key=key, scope=scope))
        db.commit()
        return True
    finally:
        db.close()
