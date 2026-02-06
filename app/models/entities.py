from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import now_utc
from app.db.base import Base


class SourceMethod(str, Enum):
    rss = "rss"
    pubmed = "pubmed"
    html = "html"
    manual = "manual"


class DocumentStatus(str, Enum):
    ingested = "ingested"
    triaged = "triaged"
    analyzed = "analyzed"
    verified = "verified"
    ready_for_review = "ready_for_review"
    approved = "approved"
    rejected = "rejected"
    bundled = "bundled"
    published = "published"


class LLMStage(str, Enum):
    triage = "triage"
    analysis = "analysis"
    verification = "verification"


class EditorStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class BundleStatus(str, Enum):
    draft = "draft"
    published = "published"


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (Index("ix_sources_active_method", "active", "method"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    method: Mapped[SourceMethod] = mapped_column(SAEnum(SourceMethod), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    poll_interval_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    trust_tier: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_raw_source_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    http_meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_html: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    source: Mapped[Source] = relationship()


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_document_id: Mapped[int] = mapped_column(ForeignKey("raw_documents.id"), unique=True, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.ingested, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    raw_document: Mapped[RawDocument] = relationship()


class DocumentDuplicate(Base):
    __tablename__ = "document_duplicates"
    __table_args__ = (
        UniqueConstraint("document_id", "duplicate_of_document_id", name="uq_document_duplicate_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    duplicate_of_document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)


class LLMRun(Base):
    __tablename__ = "llm_runs"
    __table_args__ = (Index("ix_llm_runs_doc_stage", "document_id", "stage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    stage: Mapped[LLMStage] = mapped_column(SAEnum(LLMStage), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    raw_response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), unique=True, nullable=False)
    is_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    novelty_score: Mapped[int] = mapped_column(Integer, nullable=False)
    wow_factor: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    editor_status: Mapped[EditorStatus] = mapped_column(
        SAEnum(EditorStatus), default=EditorStatus.pending, nullable=False
    )
    needs_human_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    __table_args__ = (
        CheckConstraint("novelty_score >= 1 AND novelty_score <= 10", name="ck_novelty_range"),
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_id: Mapped[int] = mapped_column(ForeignKey("insights.id"), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_strength: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    quoted_span: Mapped[str | None] = mapped_column(Text)
    supports_claim: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_id: Mapped[int] = mapped_column(ForeignKey("insights.id"), nullable=False)
    intervention: Mapped[str] = mapped_column(String(255), nullable=False)
    dose: Mapped[str] = mapped_column(String(128), nullable=False)
    population: Mapped[str | None] = mapped_column(String(255))
    duration: Mapped[str | None] = mapped_column(String(128))
    safety_notes: Mapped[str] = mapped_column(Text, nullable=False)


class PublishBundle(Base):
    __tablename__ = "publish_bundles"
    __table_args__ = (Index("ix_publish_bundles_period", "period_start", "period_end"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    beehiiv_html: Mapped[str] = mapped_column(Text, nullable=False)
    linkedin_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[BundleStatus] = mapped_column(
        SAEnum(BundleStatus), default=BundleStatus.draft, nullable=False
    )
    external_post_id: Mapped[str | None] = mapped_column(String(128))
    external_url: Mapped[str | None] = mapped_column(Text)
    publish_error: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("key", "endpoint", name="uq_idempotency_key_endpoint"),
        Index("ix_idempotency_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class EvalSample(Base):
    __tablename__ = "eval_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    label_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    label_protocol_complete: Mapped[bool | None] = mapped_column(Boolean)
    label_claim_citation_ok: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class SourceCursor(Base):
    __tablename__ = "source_cursors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), unique=True, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    cursor_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )


class JobDeadLetter(Base):
    __tablename__ = "job_dead_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class PipelineMetricDaily(Base):
    __tablename__ = "pipeline_metrics_daily"
    __table_args__ = (UniqueConstraint("metric_date", name="uq_pipeline_metric_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    ingested_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    triaged_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyzed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
