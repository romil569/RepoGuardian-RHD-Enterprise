from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("repository_id", "github_issue_number", name="uq_issue_repository_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    github_id: Mapped[int] = mapped_column(Integer, index=True)
    github_issue_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(64), index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    html_url: Mapped[str] = mapped_column(String(1024))
    analysis_status: Mapped[str] = mapped_column(String(64), default="PENDING")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="issues")
    investigations: Mapped[list["Investigation"]] = relationship(back_populates="issue")
    action_recommendations: Mapped[list["ActionRecommendation"]] = relationship(back_populates="issue")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "github_pr_number", name="uq_pr_repository_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    github_id: Mapped[int] = mapped_column(Integer, index=True)
    github_pr_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(64), index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    html_url: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("repository_id", "github_id", name="uq_comment_repository_github_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), nullable=True, index=True)
    pull_request_id: Mapped[int | None] = mapped_column(ForeignKey("pull_requests.id"), nullable=True, index=True)
    github_id: Mapped[int] = mapped_column(Integer, index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("repository_id", "tag", name="uq_release_repository_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    github_id: Mapped[int] = mapped_column(Integer, index=True)
    tag: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str] = mapped_column(String(1024))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="releases")


class RepositoryEvent(Base):
    __tablename__ = "repository_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IndexedDocument(Base):
    __tablename__ = "indexed_documents"
    __table_args__ = (UniqueConstraint("repository_id", "source_type", "source_id", name="uq_indexed_document_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    github_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(1024))
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    token_vector: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), default="COMPLETED")
    classification: Mapped[str] = mapped_column(String(64))
    classification_confidence: Mapped[float] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String(64))
    priority_confidence: Mapped[float] = mapped_column(Float)
    duplicate_probability: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_score: Mapped[int] = mapped_column(Integer)
    escalation_decision: Mapped[str] = mapped_column(String(64))
    escalation_confidence: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    issue: Mapped[Issue] = relationship(back_populates="investigations")
    evidence: Mapped[list["InvestigationEvidence"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    steps: Mapped[list["AgentExecutionStep"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    action_recommendations: Mapped[list["ActionRecommendation"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"), index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[int] = mapped_column(Integer)
    github_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(1024))
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    why_relevant: Mapped[str] = mapped_column(Text)
    retrieval_score: Mapped[float] = mapped_column(Float, default=0.0)

    investigation: Mapped[Investigation] = relationship(back_populates="evidence")


class EscalationDecision(Base):
    __tablename__ = "escalation_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"), index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    decision: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommended_action: Mapped[str] = mapped_column(Text)


class AgentExecutionStep(Base):
    __tablename__ = "agent_execution_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"), index=True)
    step_number: Mapped[int] = mapped_column(Integer)
    tool_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    investigation: Mapped[Investigation] = relationship(back_populates="steps")


class HumanFeedback(Base):
    __tablename__ = "human_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"), nullable=True, index=True)
    target_type: Mapped[str] = mapped_column(String(64))
    original_value: Mapped[str] = mapped_column(String(128))
    feedback_status: Mapped[str] = mapped_column(String(64))
    corrected_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActionRecommendation(Base):
    __tablename__ = "action_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(64), default="PENDING", index=True)
    recommended_payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    policy_decision: Mapped[str] = mapped_column(String(64), default="PENDING_REVIEW")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_result: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_signature: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    issue: Mapped[Issue] = relationship(back_populates="action_recommendations")
    investigation: Mapped[Investigation] = relationship(back_populates="action_recommendations")


class AuditLogEvent(Base):
    __tablename__ = "audit_log_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int | None] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), nullable=True, index=True)
    investigation_id: Mapped[int | None] = mapped_column(ForeignKey("investigations.id"), nullable=True, index=True)
    action_recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("action_recommendations.id"), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(255), default="system")
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    safe_summary: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
