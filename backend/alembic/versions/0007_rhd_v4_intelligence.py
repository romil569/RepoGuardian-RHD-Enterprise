"""rhd v4 intelligence

Revision ID: 0007_rhd_v4_intelligence
Revises: 0006_expand_github_ids
Create Date: 2026-08-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_rhd_v4_intelligence"
down_revision = "0006_expand_github_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rhd_agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=True),
        sa.Column("run_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="COMPLETED"),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("policy_decision", sa.String(length=64), nullable=False, server_default="READ_ONLY"),
        sa.Column("evidence_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("result", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rhd_agent_runs_repository_id", "rhd_agent_runs", ["repository_id"])
    op.create_index("ix_rhd_agent_runs_run_type", "rhd_agent_runs", ["run_type"])
    op.create_index("ix_rhd_agent_runs_status", "rhd_agent_runs", ["status"])
    op.create_index("ix_rhd_agent_runs_created_at", "rhd_agent_runs", ["created_at"])

    op.create_table(
        "rhd_agent_run_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("rhd_agent_runs.id"), nullable=False),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="COMPLETED"),
        sa.Column("tool_name", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_rhd_agent_run_steps_run_id", "rhd_agent_run_steps", ["run_id"])
    op.create_index("ix_rhd_agent_run_steps_agent_name", "rhd_agent_run_steps", ["agent_name"])

    op.create_table(
        "model_provider_telemetry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("task", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_provider_telemetry_provider", "model_provider_telemetry", ["provider"])
    op.create_index("ix_model_provider_telemetry_task", "model_provider_telemetry", ["task"])
    op.create_index("ix_model_provider_telemetry_status", "model_provider_telemetry", ["status"])
    op.create_index("ix_model_provider_telemetry_created_at", "model_provider_telemetry", ["created_at"])

    op.create_table(
        "code_symbol_index",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("symbol_name", sa.String(length=255), nullable=False),
        sa.Column("symbol_type", sa.String(length=64), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repository_id", "file_path", "symbol_name", "start_line", name="uq_code_symbol_index"),
    )
    op.create_index("ix_code_symbol_index_repository_id", "code_symbol_index", ["repository_id"])
    op.create_index("ix_code_symbol_index_file_path", "code_symbol_index", ["file_path"])
    op.create_index("ix_code_symbol_index_language", "code_symbol_index", ["language"])
    op.create_index("ix_code_symbol_index_symbol_name", "code_symbol_index", ["symbol_name"])
    op.create_index("ix_code_symbol_index_symbol_type", "code_symbol_index", ["symbol_type"])
    op.create_index("ix_code_symbol_index_indexed_at", "code_symbol_index", ["indexed_at"])

    op.create_table(
        "pr_risk_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("github_pr_number", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("recommended_reviewers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("test_recommendations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("repository_id", "pull_request_id", name="uq_pr_risk_assessment"),
    )
    op.create_index("ix_pr_risk_assessments_repository_id", "pr_risk_assessments", ["repository_id"])
    op.create_index("ix_pr_risk_assessments_pull_request_id", "pr_risk_assessments", ["pull_request_id"])
    op.create_index("ix_pr_risk_assessments_github_pr_number", "pr_risk_assessments", ["github_pr_number"])
    op.create_index("ix_pr_risk_assessments_risk_level", "pr_risk_assessments", ["risk_level"])
    op.create_index("ix_pr_risk_assessments_created_at", "pr_risk_assessments", ["created_at"])

    op.create_table(
        "blast_radius_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("pull_request_id", sa.Integer(), sa.ForeignKey("pull_requests.id"), nullable=True),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("impact_level", sa.String(length=64), nullable=False),
        sa.Column("affected_components", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_blast_radius_findings_repository_id", "blast_radius_findings", ["repository_id"])
    op.create_index("ix_blast_radius_findings_pull_request_id", "blast_radius_findings", ["pull_request_id"])
    op.create_index("ix_blast_radius_findings_scope", "blast_radius_findings", ["scope"])
    op.create_index("ix_blast_radius_findings_impact_level", "blast_radius_findings", ["impact_level"])
    op.create_index("ix_blast_radius_findings_created_at", "blast_radius_findings", ["created_at"])

    op.create_table(
        "incident_investigations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="COMPLETED"),
        sa.Column("hypotheses", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("timeline", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_incident_investigations_repository_id", "incident_investigations", ["repository_id"])
    op.create_index("ix_incident_investigations_status", "incident_investigations", ["status"])
    op.create_index("ix_incident_investigations_created_at", "incident_investigations", ["created_at"])

    op.create_table(
        "rag_evaluation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="COMPLETED"),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rag_evaluation_runs_repository_id", "rag_evaluation_runs", ["repository_id"])
    op.create_index("ix_rag_evaluation_runs_status", "rag_evaluation_runs", ["status"])
    op.create_index("ix_rag_evaluation_runs_created_at", "rag_evaluation_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("rag_evaluation_runs")
    op.drop_table("incident_investigations")
    op.drop_table("blast_radius_findings")
    op.drop_table("pr_risk_assessments")
    op.drop_table("code_symbol_index")
    op.drop_table("model_provider_telemetry")
    op.drop_table("rhd_agent_run_steps")
    op.drop_table("rhd_agent_runs")
