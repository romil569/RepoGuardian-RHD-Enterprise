from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./repoguardian-dev.db")
    data_backend: str = "sqlite"
    vector_backend: str = "local"
    deployment_mode: str = "LIGHTWEIGHT_LOCAL"
    postgres_runtime_mode: str = "local"
    redis_url: str | None = None
    queue_backend: str = "local"
    cors_origins: str = ""
    github_token: str | None = None
    openai_api_key: str | None = None
    ai_provider_mode: str = "auto"
    ai_provider_priority: str = "ollama,groq,openrouter,openai,deterministic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_timeout_seconds: int = 60
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openrouter/auto"
    openai_model: str = "gpt-4o-mini"
    allow_external_model_for_private_repos: bool = False
    github_auth_mode: str = "cli"
    github_app_id: str | None = None
    github_app_private_key_path: str | None = None
    github_app_installation_id: str | None = None
    github_webhook_secret: str | None = None
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
    allow_label_actions: bool = True
    allow_comment_actions: bool = True
    require_human_approval: bool = True
    allowed_write_repository: str = "romil569/RepoGuardian-Demo"
    max_comment_length: int = 1200
    duplicate_comment_threshold: float = 0.45
    needs_info_comment_threshold: int = 35
    security_actions_require_manual_review: bool = True
    job_max_retries: int = 3
    job_timeout_seconds: int = 300
    max_initial_code_files: int = 500
    max_initial_code_bytes: int = 5_000_000
    max_code_file_bytes: int = 200_000
    code_scan_allowed_roots: str = ""
    max_ai_calls_per_investigation: int = 4
    max_tokens_per_review: int = 6000

    def validate_policy(self) -> None:
        if not 0 <= self.duplicate_possible_threshold < self.duplicate_very_likely_threshold <= 1:
            raise ValueError("Duplicate thresholds must satisfy 0 <= possible < very_likely <= 1")
        if not 0 <= self.security_escalation_threshold <= 1:
            raise ValueError("Security threshold must be between 0 and 1")
        if self.stale_issue_days < 1:
            raise ValueError("Stale issue days must be positive")
        if not 0 <= self.high_priority_score_threshold < self.critical_priority_score_threshold <= 1:
            raise ValueError("Priority thresholds must satisfy 0 <= high < critical <= 1")
        if "/" not in self.allowed_write_repository:
            raise ValueError("Allowed write repository must be in owner/name format")
        if self.max_comment_length < 80:
            raise ValueError("Max comment length must allow a useful maintainer message")
        if not 0 <= self.duplicate_comment_threshold <= 1:
            raise ValueError("Duplicate comment threshold must be between 0 and 1")
        if not 0 <= self.needs_info_comment_threshold <= 100:
            raise ValueError("Needs-info comment threshold must be between 0 and 100")
        if self.ai_provider_mode not in {"auto", "deterministic", "openai"}:
            allowed = {"auto", "deterministic", "openai", "ollama", "groq", "openrouter"}
            if self.ai_provider_mode not in allowed:
                raise ValueError("AI provider mode must be auto, deterministic, openai, ollama, groq, or openrouter")
        if self.github_auth_mode not in {"auto", "cli", "app", "token"}:
            raise ValueError("GitHub auth mode must be auto, cli, app, or token")
        if self.deployment_mode not in {"LIGHTWEIGHT_LOCAL", "INDUSTRY_LOCAL", "MANAGED_CLOUD", "ENTERPRISE_AWS"}:
            raise ValueError("Deployment mode must be LIGHTWEIGHT_LOCAL, INDUSTRY_LOCAL, MANAGED_CLOUD, or ENTERPRISE_AWS")
        if self.postgres_runtime_mode not in {"local", "managed"}:
            raise ValueError("Postgres runtime mode must be local or managed")
        if self.queue_backend not in {"local", "postgres", "redis"}:
            raise ValueError("Queue backend must be local, postgres, or redis")
        if self.job_max_retries < 0:
            raise ValueError("Job max retries cannot be negative")
        if self.job_timeout_seconds < 1:
            raise ValueError("Job timeout must be positive")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
settings.validate_policy()
