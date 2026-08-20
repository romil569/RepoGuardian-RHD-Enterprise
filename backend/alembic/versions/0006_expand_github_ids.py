"""expand github ids

Revision ID: 0006_expand_github_ids
Revises: 0005_vercel_serverless_runtime
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_expand_github_ids"
down_revision: str | None = "0005_vercel_serverless_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.alter_column("repositories", "github_id", type_=sa.BigInteger(), existing_type=sa.Integer())
    op.alter_column("issues", "github_id", type_=sa.BigInteger(), existing_type=sa.Integer())
    op.alter_column("pull_requests", "github_id", type_=sa.BigInteger(), existing_type=sa.Integer())
    op.alter_column("comments", "github_id", type_=sa.BigInteger(), existing_type=sa.Integer())
    op.alter_column("releases", "github_id", type_=sa.BigInteger(), existing_type=sa.Integer())


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.alter_column("releases", "github_id", type_=sa.Integer(), existing_type=sa.BigInteger())
    op.alter_column("comments", "github_id", type_=sa.Integer(), existing_type=sa.BigInteger())
    op.alter_column("pull_requests", "github_id", type_=sa.Integer(), existing_type=sa.BigInteger())
    op.alter_column("issues", "github_id", type_=sa.Integer(), existing_type=sa.BigInteger())
    op.alter_column("repositories", "github_id", type_=sa.Integer(), existing_type=sa.BigInteger())
