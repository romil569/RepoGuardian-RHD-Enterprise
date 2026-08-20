from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./repoguardian-dev.db")
    data_backend: str = "sqlite"
    vector_backend: str = "local"
    github_token: str | None = None
    openai_api_key: str | None = None
    demo_github_repository: str | None = None
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    repo_sync_interval_minutes: int = 0
    github_cli_path: str | None = None
    max_investigation_steps: int = 12
    duplicate_possible_threshold: float = 0.45
    duplicate_very_likely_threshold: float = 0.72
    security_escalation_threshold: float = 0.7
    stale_issue_days: int = 30
    high_priority_score_threshold: float = 0.62
    critical_priority_score_threshold: float = 0.82

    def validate_policy(self) -> None:
        if not 0 <= self.duplicate_possible_threshold < self.duplicate_very_likely_threshold <= 1:
            raise ValueError("Duplicate thresholds must satisfy 0 <= possible < very_likely <= 1")
        if not 0 <= self.security_escalation_threshold <= 1:
            raise ValueError("Security threshold must be between 0 and 1")
        if self.stale_issue_days < 1:
            raise ValueError("Stale issue days must be positive")
        if not 0 <= self.high_priority_score_threshold < self.critical_priority_score_threshold <= 1:
            raise ValueError("Priority thresholds must satisfy 0 <= high < critical <= 1")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
settings.validate_policy()
