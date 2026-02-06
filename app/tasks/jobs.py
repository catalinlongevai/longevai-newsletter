import asyncio
from datetime import timedelta

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.core.observability import TASK_COUNT
from app.core.time import now_utc
from app.db.session import get_session_maker
from app.models.entities import (
    Document,
    DocumentStatus,
    JobDeadLetter,
    LLMStage,
    Source,
    SourceCursor,
    SourceMethod,
)
from app.schemas.common import LLMRunIn
from app.services.idempotency import cleanup_expired_keys
from app.services.ingestion.html import fetch_html_items
from app.services.ingestion.manual import create_manual_item
from app.services.ingestion.pubmed import fetch_pubmed_items
from app.services.ingestion.rss import fetch_rss_items
from app.services.llm.client import run_analysis, run_triage, run_verification
from app.services.llm.prompts import (
    ANALYSIS_PROMPT_VERSION,
    TRIAGE_PROMPT_VERSION,
    VERIFICATION_PROMPT_VERSION,
)
from app.services.pipeline import (
    apply_verification,
    bump_metric,
    run_dedup_for_document,
    save_analysis,
    store_llm_run,
    upsert_raw_document,
)
from app.state_machine.document_status import enforce_transition
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _db() -> Session:
    return get_session_maker()()


@celery_app.task(name="app.tasks.jobs.cleanup_idempotency")
def cleanup_idempotency() -> dict:
    db = _db()
    try:
        removed = cleanup_expired_keys(db)
        db.commit()
        TASK_COUNT.labels("cleanup_idempotency", "success").inc()
        return {"deleted": removed}
    except Exception:  # noqa: BLE001
        db.rollback()
        TASK_COUNT.labels("cleanup_idempotency", "failure").inc()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.jobs.ingest_sources")
def ingest_sources(source_id: int | None = None) -> dict:
    db = _db()
    try:
        sources_query = db.query(Source).filter(Source.active.is_(True))
        if source_id:
            sources_query = sources_query.filter(Source.id == source_id)
        sources = sources_query.all()

        ingested = 0
        for source in sources:
            source.last_scraped_at = now_utc()
            cooldown_sec = int((source.config_json or {}).get("cooldown_seconds", 0) or 0)
            if source.last_success_at and cooldown_sec > 0:
                if source.last_success_at + timedelta(seconds=cooldown_sec) > now_utc():
                    continue

            try:
                items = asyncio.run(_fetch_for_source(db, source))
                for item in items:
                    raw = upsert_raw_document(db, source, item.model_dump())
                    doc = db.query(Document).filter(Document.raw_document_id == raw.id).one()
                    run_dedup_for_document(db, doc)
                    triage_document.delay(doc.id)
                    ingested += 1
                source.last_success_at = now_utc()
                source.failure_count = 0
                source.last_error = None
                db.commit()
                TASK_COUNT.labels("ingest_sources", "success").inc()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                source.failure_count += 1
                source.last_error = str(exc)
                db.add(source)
                db.commit()
                _dead_letter(db, "ingest_sources", {"source_id": source.id}, exc, source_id=source.id)
                TASK_COUNT.labels("ingest_sources", "failure").inc()
        return {"ingested": ingested}
    finally:
        db.close()


async def _fetch_for_source(db: Session, source: Source):
    config = source.config_json or {}
    if source.method == SourceMethod.rss:
        cursor = db.query(SourceCursor).filter(SourceCursor.source_id == source.id).one_or_none()
        etag = cursor.etag if cursor else None
        last_modified = cursor.last_modified if cursor else None
        items, headers = await fetch_rss_items(config["url"], etag=etag, last_modified=last_modified)
        if not cursor:
            cursor = SourceCursor(source_id=source.id)
            db.add(cursor)
        cursor.etag = headers.get("etag")
        cursor.last_modified = headers.get("last_modified")
        return items
    if source.method == SourceMethod.pubmed:
        query = config.get("pubmed_query") or '(longevity OR "health span" OR aging) AND ("last 7 days"[PDat])'
        return await fetch_pubmed_items(query=query)
    if source.method == SourceMethod.html:
        selectors = config.get("selectors") or []
        return await fetch_html_items(config["url"], selectors=selectors)
    if source.method == SourceMethod.manual:
        if config.get("manual_text") and config.get("url"):
            return [
                create_manual_item(
                    url=config["url"],
                    text=config["manual_text"],
                    title=config.get("title"),
                    operator=config.get("operator", "editor"),
                )
            ]
    return []


@celery_app.task(name="app.tasks.jobs.triage_document")
def triage_document(document_id: int) -> dict:
    db = _db()
    try:
        doc = db.query(Document).filter(Document.id == document_id).one()
        triage, raw = asyncio.run(run_triage(doc.normalized_text))
        store_llm_run(
            db,
            LLMRunIn(
                document_id=doc.id,
                stage=LLMStage.triage,
                provider=raw["provider"],
                model=raw["model"],
                prompt_version=TRIAGE_PROMPT_VERSION,
                input_tokens=raw.get("input_tokens"),
                output_tokens=raw.get("output_tokens"),
                latency_ms=raw.get("latency_ms"),
                cost_usd=raw.get("cost_usd"),
                raw_response_json=raw,
            ),
        )
        if triage.is_relevant:
            enforce_transition(doc.status, DocumentStatus.triaged)
            doc.status = DocumentStatus.triaged
            bump_metric(db, "triaged_count")
            analyze_document.delay(doc.id)
        else:
            enforce_transition(doc.status, DocumentStatus.rejected)
            doc.status = DocumentStatus.rejected
            bump_metric(db, "rejected_count")
        db.commit()
        TASK_COUNT.labels("triage_document", "success").inc()
        return {"is_relevant": triage.is_relevant}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _dead_letter(db, "triage_document", {"document_id": document_id}, exc)
        TASK_COUNT.labels("triage_document", "failure").inc()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.jobs.analyze_document")
def analyze_document(document_id: int) -> dict:
    db = _db()
    try:
        doc = db.query(Document).filter(Document.id == document_id).one()
        analysis, raw = asyncio.run(run_analysis(doc.normalized_text))
        store_llm_run(
            db,
            LLMRunIn(
                document_id=doc.id,
                stage=LLMStage.analysis,
                provider=raw["provider"],
                model=raw["model"],
                prompt_version=ANALYSIS_PROMPT_VERSION,
                input_tokens=raw.get("input_tokens"),
                output_tokens=raw.get("output_tokens"),
                latency_ms=raw.get("latency_ms"),
                cost_usd=raw.get("cost_usd"),
                raw_response_json=raw,
            ),
        )
        save_analysis(db, doc, analysis)
        verify_document.delay(doc.id)
        db.commit()
        TASK_COUNT.labels("analyze_document", "success").inc()
        return {"novelty": analysis.novelty_score}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _dead_letter(db, "analyze_document", {"document_id": document_id}, exc)
        TASK_COUNT.labels("analyze_document", "failure").inc()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.jobs.verify_document")
def verify_document(document_id: int) -> dict:
    db = _db()
    try:
        doc = db.query(Document).filter(Document.id == document_id).one()
        verification, raw = asyncio.run(run_verification(doc.normalized_text))
        store_llm_run(
            db,
            LLMRunIn(
                document_id=doc.id,
                stage=LLMStage.verification,
                provider=raw["provider"],
                model=raw["model"],
                prompt_version=VERIFICATION_PROMPT_VERSION,
                input_tokens=raw.get("input_tokens"),
                output_tokens=raw.get("output_tokens"),
                latency_ms=raw.get("latency_ms"),
                cost_usd=raw.get("cost_usd"),
                raw_response_json=raw,
            ),
        )
        apply_verification(db, doc, verification)
        if doc.status == DocumentStatus.verified:
            enforce_transition(doc.status, DocumentStatus.ready_for_review)
            doc.status = DocumentStatus.ready_for_review
        db.commit()
        TASK_COUNT.labels("verify_document", "success").inc()
        return {"passed": verification.passed}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _dead_letter(db, "verify_document", {"document_id": document_id}, exc)
        TASK_COUNT.labels("verify_document", "failure").inc()
        raise
    finally:
        db.close()


def _dead_letter(
    db: Session,
    task_name: str,
    payload: dict,
    exc: Exception,
    source_id: int | None = None,
    retry_count: int = 0,
) -> None:
    logger.exception("Task failed %s", task_name)
    db.add(
        JobDeadLetter(
            task_name=task_name,
            payload_json=payload,
            source_id=source_id,
            retry_count=retry_count,
            error=str(exc),
        )
    )
    db.commit()
