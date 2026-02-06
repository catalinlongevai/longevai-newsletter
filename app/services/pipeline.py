from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import (
    Claim,
    Citation,
    Document,
    DocumentDuplicate,
    DocumentStatus,
    Insight,
    LLMRun,
    PipelineMetricDaily,
    Protocol,
    RawDocument,
    Source,
)
from app.schemas.common import AnalysisOutput, LLMRunIn, VerificationOutput
from app.state_machine.document_status import enforce_transition
from app.utils.hashing import sha256_text


def upsert_raw_document(db: Session, source: Source, item: dict) -> RawDocument:
    existing = (
        db.query(RawDocument)
        .filter(RawDocument.source_id == source.id, RawDocument.external_id == item["external_id"])
        .one_or_none()
    )
    content_hash = sha256_text((item.get("raw_text") or "") + (item.get("url") or ""))
    if existing:
        return existing

    raw_doc = RawDocument(
        source_id=source.id,
        external_id=item["external_id"],
        url=item["url"],
        raw_text=item.get("raw_text"),
        raw_html=item.get("raw_html"),
        http_meta_json=item.get("http_meta") or {},
        content_hash=content_hash,
    )
    db.add(raw_doc)
    db.flush()

    doc = Document(
        raw_document_id=raw_doc.id,
        canonical_url=item["url"],
        title=item.get("title"),
        published_at=item.get("published_at"),
        normalized_text=" ".join((item.get("raw_text") or "").split()),
        status=DocumentStatus.ingested,
    )
    db.add(doc)
    db.flush()
    _upsert_metrics(db, "ingested_count")
    return raw_doc


def run_dedup_for_document(db: Session, document: Document) -> None:
    if not document.normalized_text:
        return
    content_hash = sha256_text(document.normalized_text)
    raw = db.query(RawDocument).filter(RawDocument.id == document.raw_document_id).one()
    candidates = (
        db.query(Document)
        .join(RawDocument, RawDocument.id == Document.raw_document_id)
        .filter(RawDocument.content_hash == content_hash, Document.id != document.id)
        .limit(1)
        .all()
    )
    if candidates:
        db.add(
            DocumentDuplicate(
                document_id=document.id,
                duplicate_of_document_id=candidates[0].id,
                similarity_score=1.0,
                method="hash_exact",
            )
        )
    raw.content_hash = content_hash


def store_llm_run(db: Session, run_in: LLMRunIn) -> None:
    db.add(
        LLMRun(
            document_id=run_in.document_id,
            stage=run_in.stage,
            provider=run_in.provider,
            model=run_in.model,
            prompt_version=run_in.prompt_version,
            input_tokens=run_in.input_tokens,
            output_tokens=run_in.output_tokens,
            latency_ms=run_in.latency_ms,
            cost_usd=run_in.cost_usd,
            raw_response_json=run_in.raw_response_json,
        )
    )


def save_analysis(db: Session, document: Document, analysis: AnalysisOutput) -> Insight:
    insight = db.query(Insight).filter(Insight.document_id == document.id).one_or_none()
    if not insight:
        insight = Insight(
            document_id=document.id,
            is_relevant=True,
            novelty_score=analysis.novelty_score,
            wow_factor=analysis.wow_factor,
            confidence_label=analysis.confidence_label,
            summary_markdown=analysis.summary_markdown,
            needs_human_verification=analysis.needs_human_verification,
        )
        db.add(insight)
        db.flush()
    else:
        insight.novelty_score = analysis.novelty_score
        insight.wow_factor = analysis.wow_factor
        insight.confidence_label = analysis.confidence_label
        insight.summary_markdown = analysis.summary_markdown
        insight.needs_human_verification = analysis.needs_human_verification

    existing_claims = db.query(Claim).filter(Claim.insight_id == insight.id).all()
    if existing_claims:
        existing_claim_ids = [claim.id for claim in existing_claims]
        db.query(Citation).filter(Citation.claim_id.in_(existing_claim_ids)).delete(
            synchronize_session=False
        )
    db.query(Claim).filter(Claim.insight_id == insight.id).delete()
    db.query(Protocol).filter(Protocol.insight_id == insight.id).delete()

    for claim, citation_set in zip(analysis.claims, analysis.citations, strict=False):
        claim_row = Claim(
            insight_id=insight.id,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            confidence_score=claim.confidence_score,
            evidence_strength=claim.evidence_strength,
            risk_flags_json=claim.risk_flags_json,
        )
        db.add(claim_row)
        db.flush()
        for citation in citation_set:
            db.add(
                Citation(
                    claim_id=claim_row.id,
                    source_url=citation.source_url,
                    source_type=citation.source_type,
                    quoted_span=citation.quoted_span,
                    supports_claim=citation.supports_claim,
                )
            )

    for protocol in analysis.protocols:
        if not any(ch.isdigit() for ch in protocol.dose):
            raise ValueError("Protocol dose must include units or numeric quantity")
        if not protocol.safety_notes.strip():
            raise ValueError("Protocol safety_notes cannot be empty")
        db.add(
            Protocol(
                insight_id=insight.id,
                intervention=protocol.intervention,
                dose=protocol.dose,
                population=protocol.population,
                duration=protocol.duration,
                safety_notes=protocol.safety_notes,
            )
        )

    enforce_transition(document.status, DocumentStatus.analyzed)
    document.status = DocumentStatus.analyzed
    _upsert_metrics(db, "analyzed_count")
    return insight


def apply_verification(db: Session, document: Document, verification: VerificationOutput) -> None:
    if verification.passed:
        enforce_transition(document.status, DocumentStatus.verified)
        document.status = DocumentStatus.verified
        _upsert_metrics(db, "verified_count")
    else:
        enforce_transition(document.status, DocumentStatus.rejected)
        document.status = DocumentStatus.rejected
        _upsert_metrics(db, "rejected_count")


def _upsert_metrics(db: Session, field: str) -> None:
    today = date.today()
    metrics = db.query(PipelineMetricDaily).filter(PipelineMetricDaily.metric_date == today).one_or_none()
    if not metrics:
        metrics = PipelineMetricDaily(
            metric_date=today,
            ingested_count=0,
            triaged_count=0,
            analyzed_count=0,
            verified_count=0,
            approved_count=0,
            rejected_count=0,
        )
        db.add(metrics)
        db.flush()
    current_value = getattr(metrics, field)
    setattr(metrics, field, current_value + 1)


def bump_metric(db: Session, field: str) -> None:
    _upsert_metrics(db, field)


def get_pipeline_metrics(db: Session) -> dict:
    today = date.today()
    metrics = db.query(PipelineMetricDaily).filter(PipelineMetricDaily.metric_date == today).one_or_none()
    if not metrics:
        return {
            "today_ingested": 0,
            "today_triaged": 0,
            "today_analyzed": 0,
            "today_verified": 0,
            "today_approved": 0,
            "today_rejected": 0,
        }
    return {
        "today_ingested": metrics.ingested_count,
        "today_triaged": metrics.triaged_count,
        "today_analyzed": metrics.analyzed_count,
        "today_verified": metrics.verified_count,
        "today_approved": metrics.approved_count,
        "today_rejected": metrics.rejected_count,
    }


def count_inbox(db: Session) -> int:
    return (
        db.query(func.count(Insight.id))
        .join(Document, Document.id == Insight.document_id)
        .filter(Document.status == DocumentStatus.ready_for_review)
        .scalar()
        or 0
    )
