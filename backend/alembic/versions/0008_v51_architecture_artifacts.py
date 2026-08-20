"""v51 architecture artifacts

Revision ID: 0008_v51_architecture_artifacts
Revises: 0007_rhd_v4_intelligence
Create Date: 2026-08-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_v51_architecture_artifacts"
down_revision = "0007_rhd_v4_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "architecture_artifacts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("diagram_source", sa.Text(), nullable=False),
        sa.Column("svg", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("evidence_version", sa.String(length=128), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repository_id", "artifact_type", "evidence_version", name="uq_architecture_artifact_version"),
    )
    op.create_index("ix_architecture_artifacts_repository_id", "architecture_artifacts", ["repository_id"])
    op.create_index("ix_architecture_artifacts_conversation_id", "architecture_artifacts", ["conversation_id"])
    op.create_index("ix_architecture_artifacts_commit_sha", "architecture_artifacts", ["commit_sha"])
    op.create_index("ix_architecture_artifacts_artifact_type", "architecture_artifacts", ["artifact_type"])
    op.create_index("ix_architecture_artifacts_evidence_version", "architecture_artifacts", ["evidence_version"])
    op.create_index("ix_architecture_artifacts_generated_at", "architecture_artifacts", ["generated_at"])


def downgrade() -> None:
    op.drop_table("architecture_artifacts")
