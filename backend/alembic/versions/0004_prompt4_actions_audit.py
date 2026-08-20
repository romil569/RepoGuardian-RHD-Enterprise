"""prompt 4 actions and audit log

Revision ID: 0004_prompt4_actions_audit
Revises: 0003_prompt3_feedback
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_prompt4_actions_audit"
down_revision: str | None = "0003_prompt3_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("investigation_id", sa.Integer(), sa.ForeignKey("investigations.id"), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PENDING"),
        sa.Column("recommended_payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("policy_decision", sa.String(length=64), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(length=255), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_status", sa.String(length=64), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("execution_signature", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_action_recommendations_repository_id", "action_recommendations", ["repository_id"])
    op.create_index("ix_action_recommendations_issue_id", "action_recommendations", ["issue_id"])
    op.create_index("ix_action_recommendations_investigation_id", "action_recommendations", ["investigation_id"])
    op.create_index("ix_action_recommendations_action_type", "action_recommendations", ["action_type"])
    op.create_index("ix_action_recommendations_status", "action_recommendations", ["status"])
    op.create_index("ix_action_recommendations_execution_signature", "action_recommendations", ["execution_signature"])

    op.create_table(
        "audit_log_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=True),
        sa.Column("investigation_id", sa.Integer(), sa.ForeignKey("investigations.id"), nullable=True),
        sa.Column("action_recommendation_id", sa.Integer(), sa.ForeignKey("action_recommendations.id"), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=False, server_default="system"),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("safe_summary", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_events_repository_id", "audit_log_events", ["repository_id"])
    op.create_index("ix_audit_log_events_issue_id", "audit_log_events", ["issue_id"])
    op.create_index("ix_audit_log_events_investigation_id", "audit_log_events", ["investigation_id"])
    op.create_index("ix_audit_log_events_action_recommendation_id", "audit_log_events", ["action_recommendation_id"])
    op.create_index("ix_audit_log_events_event_type", "audit_log_events", ["event_type"])
    op.create_index("ix_audit_log_events_created_at", "audit_log_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log_events")
    op.drop_table("action_recommendations")
