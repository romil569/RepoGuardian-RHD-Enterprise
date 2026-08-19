from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://repoguardian:repoguardian_dev_password@localhost:5432/repoguardian"
    )
    github_token: str | None = None
    openai_api_key: str | None = None
    demo_github_repository: str | None = None
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
