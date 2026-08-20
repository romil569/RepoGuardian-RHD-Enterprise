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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
