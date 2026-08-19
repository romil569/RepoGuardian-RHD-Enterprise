from app.core.config import settings


def is_demo_repository_allowed(full_name: str) -> bool:
    return bool(settings.demo_github_repository and full_name == settings.demo_github_repository)
