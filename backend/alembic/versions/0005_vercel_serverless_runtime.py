"""vercel serverless runtime primitives

Revision ID: 0005_vercel_serverless_runtime
Revises: 0004_prompt4_actions_audit
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_vercel_serverless_runtime"
down_revision: str | None = "0004_prompt4_actions_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deployment_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=True),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="QUEUED"),
        sa.Column("stage", sa.String(length=128), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("correlation_id", name="uq_deployment_jobs_correlation_id"),
    )
    op.create_index("ix_deployment_jobs_repository_id", "deployment_jobs", ["repository_id"])
    op.create_index("ix_deployment_jobs_job_type", "deployment_jobs", ["job_type"])
    op.create_index("ix_deployment_jobs_status", "deployment_jobs", ["status"])
    op.create_index("ix_deployment_jobs_stage", "deployment_jobs", ["stage"])
    op.create_index("ix_deployment_jobs_lease_until", "deployment_jobs", ["lease_until"])
    op.create_index("ix_deployment_jobs_correlation_id", "deployment_jobs", ["correlation_id"])
    op.create_index("ix_deployment_jobs_created_at", "deployment_jobs", ["created_at"])

    op.create_table(
        "public_rate_limit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_public_rate_limit_events_key", "public_rate_limit_events", ["key"])
    op.create_index("ix_public_rate_limit_events_scope", "public_rate_limit_events", ["scope"])
    op.create_index("ix_public_rate_limit_events_created_at", "public_rate_limit_events", ["created_at"])

    op.create_table(
        "public_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_public_sessions_repository_id", "public_sessions", ["repository_id"])
    op.create_index("ix_public_sessions_created_at", "public_sessions", ["created_at"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("public_sessions.id"), nullable=False),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversation_messages_session_id", "conversation_messages", ["session_id"])
    op.create_index("ix_conversation_messages_repository_id", "conversation_messages", ["repository_id"])
    op.create_index("ix_conversation_messages_created_at", "conversation_messages", ["created_at"])

    op.create_table(
        "repository_graph_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("node_id", sa.String(length=512), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repository_id", "node_id", name="uq_repository_graph_node"),
    )
    op.create_index("ix_repository_graph_nodes_repository_id", "repository_graph_nodes", ["repository_id"])
    op.create_index("ix_repository_graph_nodes_node_id", "repository_graph_nodes", ["node_id"])

    op.create_table(
        "repository_graph_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("source_node_id", sa.String(length=512), nullable=False),
        sa.Column("target_node_id", sa.String(length=512), nullable=False),
        sa.Column("edge_type", sa.String(length=128), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_repository_graph_edges_repository_id", "repository_graph_edges", ["repository_id"])
    op.create_index("ix_repository_graph_edges_source_node_id", "repository_graph_edges", ["source_node_id"])
    op.create_index("ix_repository_graph_edges_target_node_id", "repository_graph_edges", ["target_node_id"])
    op.create_index("ix_repository_graph_edges_edge_type", "repository_graph_edges", ["edge_type"])


def downgrade() -> None:
    op.drop_table("repository_graph_edges")
    op.drop_table("repository_graph_nodes")
    op.drop_table("conversation_messages")
    op.drop_table("public_sessions")
    op.drop_table("public_rate_limit_events")
    op.drop_table("deployment_jobs")
