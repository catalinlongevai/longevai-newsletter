"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    source_method = sa.Enum("rss", "pubmed", "html", "manual", name="sourcemethod")
    document_status = sa.Enum(
        "ingested",
        "triaged",
        "analyzed",
        "verified",
        "ready_for_review",
        "approved",
        "rejected",
        "bundled",
        "published",
        name="documentstatus",
    )
    llm_stage = sa.Enum("triage", "analysis", "verification", name="llmstage")
    editor_status = sa.Enum("pending", "approved", "rejected", name="editorstatus")
    bundle_status = sa.Enum("draft", "published", name="bundlestatus")

    source_method.create(bind, checkfirst=True)
    document_status.create(bind, checkfirst=True)
    llm_stage.create(bind, checkfirst=True)
    editor_status.create(bind, checkfirst=True)
    bundle_status.create(bind, checkfirst=True)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("method", source_method, nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("poll_interval_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("trust_tier", sa.String(length=50), nullable=False, server_default="standard"),
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sources_active_method", "sources", ["active", "method"])

    op.create_table(
        "raw_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("http_meta_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_source_external"),
    )
    op.create_index("ix_raw_documents_content_hash", "raw_documents", ["content_hash"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_document_id", sa.Integer(), sa.ForeignKey("raw_documents.id"), nullable=False, unique=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("status", document_status, nullable=False, server_default="ingested"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "document_duplicates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("duplicate_of_document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("document_id", "duplicate_of_document_id", name="uq_document_duplicate_pair"),
    )

    op.create_table(
        "llm_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("stage", llm_stage, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("raw_response_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_llm_runs_doc_stage", "llm_runs", ["document_id", "stage"])

    op.create_table(
        "insights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False, unique=True),
        sa.Column("is_relevant", sa.Boolean(), nullable=False),
        sa.Column("novelty_score", sa.Integer(), nullable=False),
        sa.Column("wow_factor", sa.Text(), nullable=False),
        sa.Column("confidence_label", sa.String(length=64), nullable=False),
        sa.Column("summary_markdown", sa.Text(), nullable=False),
        sa.Column("editor_status", editor_status, nullable=False, server_default="pending"),
        sa.Column("needs_human_verification", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("novelty_score >= 1 AND novelty_score <= 10", name="ck_novelty_range"),
    )

    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("insight_id", sa.Integer(), sa.ForeignKey("insights.id"), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("evidence_strength", sa.String(length=64), nullable=False),
        sa.Column("risk_flags_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("quoted_span", sa.Text(), nullable=True),
        sa.Column("supports_claim", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "protocols",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("insight_id", sa.Integer(), sa.ForeignKey("insights.id"), nullable=False),
        sa.Column("intervention", sa.String(length=255), nullable=False),
        sa.Column("dose", sa.String(length=128), nullable=False),
        sa.Column("population", sa.String(length=255), nullable=True),
        sa.Column("duration", sa.String(length=128), nullable=True),
        sa.Column("safety_notes", sa.Text(), nullable=False),
    )

    op.create_table(
        "publish_bundles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("beehiiv_html", sa.Text(), nullable=False),
        sa.Column("linkedin_text", sa.Text(), nullable=False),
        sa.Column("status", bundle_status, nullable=False, server_default="draft"),
        sa.Column("external_post_id", sa.String(length=128), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("publish_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_publish_bundles_period", "publish_bundles", ["period_start", "period_end"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("key", "endpoint", name="uq_idempotency_key_endpoint"),
    )
    op.create_index("ix_idempotency_created_at", "idempotency_keys", ["created_at"])

    op.create_table(
        "eval_samples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("label_relevant", sa.Boolean(), nullable=False),
        sa.Column("label_protocol_complete", sa.Boolean(), nullable=True),
        sa.Column("label_claim_citation_ok", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "source_cursors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False, unique=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.Column("cursor_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "job_dead_letters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "pipeline_metrics_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("ingested_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("triaged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analyzed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("metric_date", name="uq_pipeline_metric_date"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_metrics_daily")
    op.drop_table("job_dead_letters")
    op.drop_table("source_cursors")
    op.drop_table("eval_samples")
    op.drop_index("ix_idempotency_created_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_table("audit_logs")
    op.drop_index("ix_publish_bundles_period", table_name="publish_bundles")
    op.drop_table("publish_bundles")
    op.drop_table("protocols")
    op.drop_table("citations")
    op.drop_table("claims")
    op.drop_table("insights")
    op.drop_index("ix_llm_runs_doc_stage", table_name="llm_runs")
    op.drop_table("llm_runs")
    op.drop_table("document_duplicates")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_raw_documents_content_hash", table_name="raw_documents")
    op.drop_table("raw_documents")
    op.drop_index("ix_sources_active_method", table_name="sources")
    op.drop_table("sources")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="bundlestatus").drop(bind, checkfirst=True)
        sa.Enum(name="editorstatus").drop(bind, checkfirst=True)
        sa.Enum(name="llmstage").drop(bind, checkfirst=True)
        sa.Enum(name="documentstatus").drop(bind, checkfirst=True)
        sa.Enum(name="sourcemethod").drop(bind, checkfirst=True)
