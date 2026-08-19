from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RepositoryRead(BaseModel):
    id: int
    github_id: int
    owner: str
    name: str
    full_name: str
    description: str | None
    html_url: str
    default_branch: str
    language: str | None
    stars: int
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
