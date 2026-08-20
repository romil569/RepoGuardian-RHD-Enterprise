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
        "allow_label_actions": settings.allow_label_actions,
        "allow_comment_actions": settings.allow_comment_actions,
        "require_human_approval": settings.require_human_approval,
        "allowed_write_repository": settings.allowed_write_repository,
        "max_comment_length": settings.max_comment_length,
        "duplicate_comment_threshold": settings.duplicate_comment_threshold,
        "needs_info_comment_threshold": settings.needs_info_comment_threshold,
        "security_actions_require_manual_review": settings.security_actions_require_manual_review,
    }
