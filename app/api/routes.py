from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Any

from app.db.session import get_db
from app.models.entities import (
    BundleStatus,
    Claim,
    Citation,
    Document,
    DocumentStatus,
    EditorStatus,
    Insight,
    LLMRun,
    Protocol,
    PublishBundle,
    RawDocument,
    Source,
    SourceMethod,
)
from app.schemas import (
    BuildBundleRequest,
    CitationOut,
    ClaimOut,
    DocumentStatusTransition,
    InboxResponse,
    IngestRunRequest,
    InsightDetailOut,
    InsightOut,
    InsightPatch,
    LLMRunOut,
    ManualIngestRequest,
    PipelineMetricsOut,
    ProtocolOut,
    SourceCreate,
    SourceOut,
    SourceUpdate,
)
from app.services.audit import record_audit
from app.services.idempotency import resolve_cached_response, store_response
from app.services.pipeline import bump_metric, get_pipeline_metrics, upsert_raw_document
from app.services.publish.beehiiv import publish_draft
from app.services.publish.bundle import build_bundle
from app.state_machine.document_status import enforce_transition
from app.tasks.celery_app import celery_app
from app.tasks.jobs import ingest_sources, triage_document
from app.core.responses import success_response
from app.core.time import now_utc

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.name.asc()).all()
    return success_response([SourceOut.model_validate(source).model_dump(mode="json") for source in sources])


@router.post("/sources")
def create_source(
    payload: SourceCreate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, "/v1/sources", payload.model_dump())
    if cached:
        return success_response(cached)

    source = Source(**payload.model_dump())
    db.add(source)
    db.flush()
    record_audit(db, "system", "create", "source", source.id, payload.model_dump())
    response = SourceOut.model_validate(source).model_dump(mode="json")
    store_response(db, idempotency_key, "/v1/sources", payload.model_dump(), response)
    db.commit()
    return success_response(response)


@router.patch("/sources/{source_id}")
def update_source(
    source_id: int,
    payload: SourceUpdate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, f"/v1/sources/{source_id}", payload.model_dump())
    if cached:
        return success_response(cached)

    source = db.query(Source).filter(Source.id == source_id).one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(source, key, value)

    record_audit(db, "system", "update", "source", source.id, payload.model_dump(exclude_none=True))
    response = SourceOut.model_validate(source).model_dump(mode="json")
    store_response(db, idempotency_key, f"/v1/sources/{source_id}", payload.model_dump(), response)
    db.commit()
    return success_response(response)


@router.post("/manual-ingest")
def manual_ingest(
    payload: ManualIngestRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, "/v1/manual-ingest", payload.model_dump())
    if cached:
        return success_response(cached)

    source = db.query(Source).filter(Source.name == payload.source_name).one_or_none()
    if not source:
        source = Source(
            name=payload.source_name,
            method=SourceMethod.manual,
            config_json={},
            active=True,
            poll_interval_min=1440,
            trust_tier="manual",
        )
        db.add(source)
        db.flush()

    raw = upsert_raw_document(
        db,
        source,
        {
            "external_id": payload.url,
            "url": payload.url,
            "title": payload.title,
            "raw_text": payload.text,
            "raw_html": payload.text,
            "http_meta": {"manual": True, "operator": payload.operator},
        },
    )
    document = db.query(Document).filter(Document.raw_document_id == raw.id).one()
    task = triage_document.delay(document.id)

    record_audit(
        db,
        payload.operator,
        "manual_ingest",
        "document",
        document.id,
        payload.model_dump(),
    )
    response = {"document_id": document.id, "task_id": task.id}
    store_response(db, idempotency_key, "/v1/manual-ingest", payload.model_dump(), response)
    db.commit()
    return success_response(response)


@router.post("/ingest/run")
def run_ingest(
    payload: IngestRunRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, "/v1/ingest/run", payload.model_dump())
    if cached:
        return success_response(cached)

    task = ingest_sources.delay(payload.source_id)
    response = {"task_id": task.id, "source_id": payload.source_id}
    store_response(db, idempotency_key, "/v1/ingest/run", payload.model_dump(), response)
    db.commit()
    return success_response(response)


@router.get("/tasks/{task_id}")
def task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    return success_response({"task_id": task_id, "state": result.state, "result": result.result})


@router.get("/inbox")
def get_inbox(
    status: DocumentStatus | None = Query(default=DocumentStatus.ready_for_review),
    needs_human_verification: bool | None = Query(default=None),
    min_novelty: int = Query(default=1, ge=1, le=10),
    source_id: int | None = Query(default=None),
    sort: str = Query(default="novelty_score"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Insight).join(Document, Document.id == Insight.document_id)

    if status:
        query = query.filter(Document.status == status)
    if needs_human_verification is not None:
        query = query.filter(Insight.needs_human_verification == needs_human_verification)
    if min_novelty:
        query = query.filter(Insight.novelty_score >= min_novelty)
    if source_id:
        query = (
            query.join(RawDocument, RawDocument.id == Document.raw_document_id)
            .filter(RawDocument.source_id == source_id)
        )

    total = query.count()
    sort_col: Any
    if sort == "novelty_score":
        sort_col = Insight.novelty_score
    else:
        sort_col = Insight.created_at

    query = query.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    items = query.offset(offset).limit(limit).all()

    payload = InboxResponse(items=[InsightOut.model_validate(item) for item in items], total=total)
    return success_response(
        payload.model_dump(mode="json"),
        meta={"limit": limit, "offset": offset, "sort": sort, "order": order},
    )


@router.get("/insights/{insight_id}")
def insight_detail(insight_id: int, db: Session = Depends(get_db)):
    insight = db.query(Insight).filter(Insight.id == insight_id).one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    claims = db.query(Claim).filter(Claim.insight_id == insight_id).all()
    claim_ids = [c.id for c in claims]
    citations = db.query(Citation).filter(Citation.claim_id.in_(claim_ids)).all() if claim_ids else []
    protocols = db.query(Protocol).filter(Protocol.insight_id == insight_id).all()
    llm_runs = db.query(LLMRun).filter(LLMRun.document_id == insight.document_id).all()

    payload = InsightDetailOut(
        insight=InsightOut.model_validate(insight),
        claims=[ClaimOut.model_validate(claim) for claim in claims],
        citations=[CitationOut.model_validate(citation) for citation in citations],
        protocols=[ProtocolOut.model_validate(protocol) for protocol in protocols],
        llm_runs=[LLMRunOut.model_validate(run) for run in llm_runs],
    )
    return success_response(payload.model_dump(mode="json"))


@router.post("/documents/{document_id}/transition")
def transition_document_status(
    document_id: int,
    payload: DocumentStatusTransition,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(
        db,
        request,
        f"/v1/documents/{document_id}/transition",
        payload.model_dump(mode="json"),
    )
    if cached:
        return success_response(cached)

    doc = db.query(Document).filter(Document.id == document_id).one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != payload.current:
        raise HTTPException(status_code=409, detail="Document status mismatch")

    enforce_transition(doc.status, payload.target)
    doc.status = payload.target
    record_audit(
        db,
        "editor",
        "transition",
        "document",
        doc.id,
        payload.model_dump(mode="json"),
    )
    response = {"document_id": doc.id, "status": doc.status.value}
    store_response(
        db,
        idempotency_key,
        f"/v1/documents/{document_id}/transition",
        payload.model_dump(mode="json"),
        response,
    )
    db.commit()
    return success_response(response)


@router.post("/insights/{insight_id}/approve")
def approve_insight(
    insight_id: int,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, f"/v1/insights/{insight_id}/approve", {})
    if cached:
        return success_response(cached)

    insight = db.query(Insight).filter(Insight.id == insight_id).one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    if insight.needs_human_verification:
        raise HTTPException(status_code=409, detail="Insight requires human verification")

    doc = db.query(Document).filter(Document.id == insight.document_id).one()
    enforce_transition(doc.status, DocumentStatus.approved)
    doc.status = DocumentStatus.approved
    insight.editor_status = EditorStatus.approved
    bump_metric(db, "approved_count")
    record_audit(db, "editor", "approve", "insight", insight.id, {})

    response = InsightOut.model_validate(insight).model_dump(mode="json")
    store_response(db, idempotency_key, f"/v1/insights/{insight_id}/approve", {}, response)
    db.commit()
    return success_response(response)


@router.post("/insights/{insight_id}/reject")
def reject_insight(
    insight_id: int,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, f"/v1/insights/{insight_id}/reject", {})
    if cached:
        return success_response(cached)

    insight = db.query(Insight).filter(Insight.id == insight_id).one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    doc = db.query(Document).filter(Document.id == insight.document_id).one()
    enforce_transition(doc.status, DocumentStatus.rejected)
    doc.status = DocumentStatus.rejected
    insight.editor_status = EditorStatus.rejected
    bump_metric(db, "rejected_count")
    record_audit(db, "editor", "reject", "insight", insight.id, {})

    response = InsightOut.model_validate(insight).model_dump(mode="json")
    store_response(db, idempotency_key, f"/v1/insights/{insight_id}/reject", {}, response)
    db.commit()
    return success_response(response)


@router.patch("/insights/{insight_id}")
def patch_insight(
    insight_id: int,
    payload: InsightPatch,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, f"/v1/insights/{insight_id}", payload.model_dump())
    if cached:
        return success_response(cached)

    insight = db.query(Insight).filter(Insight.id == insight_id).one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(insight, key, value)

    record_audit(db, "editor", "edit", "insight", insight.id, payload.model_dump(exclude_none=True))
    response = InsightOut.model_validate(insight).model_dump(mode="json")
    store_response(db, idempotency_key, f"/v1/insights/{insight_id}", payload.model_dump(), response)
    db.commit()
    return success_response(response)


@router.post("/bundles/build")
def create_bundle(
    request_payload: BuildBundleRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    payload = request_payload.model_dump(mode="json")
    cached = resolve_cached_response(db, request, "/v1/bundles/build", payload)
    if cached:
        return success_response(cached)

    bundle = build_bundle(
        db,
        request_payload.start,
        request_payload.end,
        insight_ids=request_payload.insight_ids,
    )
    record_audit(db, "editor", "build", "publish_bundle", bundle.id, payload)
    response = {
        "id": bundle.id,
        "status": bundle.status.value,
        "period_start": bundle.period_start.isoformat(),
        "period_end": bundle.period_end.isoformat(),
    }
    store_response(db, idempotency_key, "/v1/bundles/build", payload, response)
    db.commit()
    return success_response(response)


@router.post("/bundles/{bundle_id}/publish/beehiiv")
async def publish_bundle(
    bundle_id: int,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    cached = resolve_cached_response(db, request, f"/v1/bundles/{bundle_id}/publish/beehiiv", {})
    if cached:
        return success_response(cached)

    bundle = db.query(PublishBundle).filter(PublishBundle.id == bundle_id).one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    result = await publish_draft(bundle.beehiiv_html)
    if result.get("status") == "ok":
        bundle.status = BundleStatus.published
        bundle.published_at = now_utc()
        bundle.external_post_id = result.get("external_post_id")
        bundle.external_url = result.get("external_url")
        bundle.publish_error = None

        docs = (
            db.query(Document)
            .join(Insight, Insight.document_id == Document.id)
            .filter(
                Insight.editor_status == EditorStatus.approved,
                Insight.created_at >= bundle.period_start,
                Insight.created_at <= bundle.period_end,
            )
            .all()
        )
        for doc in docs:
            if doc.status == DocumentStatus.bundled:
                enforce_transition(doc.status, DocumentStatus.published)
                doc.status = DocumentStatus.published
    else:
        bundle.publish_error = result.get("error") or result.get("reason")

    response = {"bundle_id": bundle.id, "publish_result": result}
    store_response(db, idempotency_key, f"/v1/bundles/{bundle_id}/publish/beehiiv", {}, response)
    db.commit()
    return success_response(response)


@router.get("/metrics/pipeline")
def pipeline_metrics(db: Session = Depends(get_db)):
    payload = PipelineMetricsOut(**get_pipeline_metrics(db))
    return success_response(payload.model_dump())
