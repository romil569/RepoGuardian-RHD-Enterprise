from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/policy")
def get_policy() -> dict[str, object]:
    return {
        "duplicate_possible_threshold": settings.duplicate_possible_threshold,
        "duplicate_very_likely_threshold": settings.duplicate_very_likely_threshold,
        "security_escalation_threshold": settings.security_escalation_threshold,
        "stale_issue_days": settings.stale_issue_days,
        "high_priority_score_threshold": settings.high_priority_score_threshold,
        "critical_priority_score_threshold": settings.critical_priority_score_threshold,
        "repo_sync_interval_minutes": settings.repo_sync_interval_minutes,
    }
