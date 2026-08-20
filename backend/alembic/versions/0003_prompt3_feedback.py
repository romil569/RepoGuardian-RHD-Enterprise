"""prompt 3 feedback table

Revision ID: 0003_prompt3_feedback
Revises: 0002_repository_intelligence
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_prompt3_feedback"
down_revision: str | None = "0002_repository_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "human_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("investigation_id", sa.Integer(), sa.ForeignKey("investigations.id"), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("original_value", sa.String(length=128), nullable=False),
        sa.Column("feedback_status", sa.String(length=64), nullable=False),
        sa.Column("corrected_value", sa.String(length=128), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("human_feedback")
