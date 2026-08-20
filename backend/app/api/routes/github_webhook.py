from fastapi import APIRouter

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/webhook")
def github_webhook_placeholder() -> dict[str, str]:
    return {"status": "accepted", "mode": "webhook-ready-placeholder"}
