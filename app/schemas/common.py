from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

from app.models.entities import (
    DocumentStatus,
    EditorStatus,
    LLMStage,
    SourceMethod,
)


class ApiError(BaseModel):
    code: str
    message: str
    trace_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiEnvelope(BaseModel):
    data: Any = None
    error: ApiError | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class SourceConfig(BaseModel):
    url: HttpUrl | None = None
    pubmed_query: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    selectors: list[str] = Field(default_factory=list)
    cooldown_seconds: int = Field(default=0, ge=0)


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    method: SourceMethod
    config_json: SourceConfig | dict
    active: bool = True
    poll_interval_min: int = Field(default=60, ge=1, le=10080)
    trust_tier: str = Field(default="standard", max_length=50)


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    config_json: SourceConfig | dict | None = None
    active: bool | None = None
    poll_interval_min: int | None = Field(default=None, ge=1, le=10080)
    trust_tier: str | None = Field(default=None, max_length=50)


class SourceOut(BaseModel):
    id: int
    name: str
    method: SourceMethod
    config_json: dict
    active: bool
    poll_interval_min: int
    trust_tier: str
    last_scraped_at: datetime | None = None
    last_success_at: datetime | None = None
    next_scheduled_at: datetime | None = None
    last_error: str | None = None
    failure_count: int

    model_config = {"from_attributes": True}


class IngestRunRequest(BaseModel):
    source_id: int | None = None


class ManualIngestRequest(BaseModel):
    source_name: str
    url: str
    text: str
    title: str | None = None
    operator: str = "editor"


class InsightOut(BaseModel):
    id: int
    document_id: int
    is_relevant: bool
    novelty_score: int
    wow_factor: str
    confidence_label: str
    summary_markdown: str
    editor_status: EditorStatus
    needs_human_verification: bool

    model_config = {"from_attributes": True}


class ClaimOut(BaseModel):
    id: int
    claim_text: str
    claim_type: str
    confidence_score: float
    evidence_strength: str
    risk_flags_json: dict

    model_config = {"from_attributes": True}


class CitationOut(BaseModel):
    id: int
    claim_id: int
    source_url: str
    source_type: str
    quoted_span: str | None
    supports_claim: bool

    model_config = {"from_attributes": True}


class ProtocolOut(BaseModel):
    id: int
    intervention: str
    dose: str
    population: str | None
    duration: str | None
    safety_notes: str

    model_config = {"from_attributes": True}


class LLMRunOut(BaseModel):
    id: int
    stage: LLMStage
    provider: str
    model: str
    prompt_version: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    cost_usd: float | None
    raw_response_json: dict = Field(default_factory=dict)
    prompt_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightDetailOut(BaseModel):
    insight: InsightOut
    claims: list[ClaimOut]
    citations: list[CitationOut]
    protocols: list[ProtocolOut]
    llm_runs: list[LLMRunOut]


class SourceRunOut(BaseModel):
    id: int
    source_id: int
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    items_discovered: int
    items_ingested: int
    error: str | None

    model_config = {"from_attributes": True}


class RawDocumentListItemOut(BaseModel):
    id: int
    source_id: int
    source_name: str
    external_id: str
    url: str
    fetched_at: datetime
    title: str | None = None
    status: DocumentStatus
    text_preview: str


class RawDocumentDetailOut(BaseModel):
    id: int
    source_id: int
    source_name: str
    external_id: str
    url: str
    fetched_at: datetime
    http_meta_json: dict
    raw_text: str | None = None
    raw_html: str | None = None
    content_hash: str
    document_id: int
    title: str | None = None
    published_at: datetime | None = None
    status: DocumentStatus
    normalized_text: str
    llm_runs: list[LLMRunOut] = Field(default_factory=list)


class InboxResponse(BaseModel):
    items: list[InsightOut]
    total: int


class InsightPatch(BaseModel):
    wow_factor: str | None = None
    summary_markdown: str | None = None
    confidence_label: str | None = None


class BuildBundleRequest(BaseModel):
    start: datetime
    end: datetime
    insight_ids: list[int] | None = None


class PipelineMetricsOut(BaseModel):
    today_ingested: int
    today_triaged: int
    today_analyzed: int
    today_verified: int
    today_approved: int
    today_rejected: int


class ClaimModel(BaseModel):
    claim_text: str
    claim_type: str
    confidence_score: float = Field(ge=0, le=1)
    evidence_strength: Literal["weak", "moderate", "strong"]
    risk_flags_json: dict = Field(default_factory=dict)


class CitationModel(BaseModel):
    source_url: str
    source_type: str
    quoted_span: str | None = None
    supports_claim: bool = True


class ProtocolModel(BaseModel):
    intervention: str
    dose: str
    population: str | None = None
    duration: str | None = None
    safety_notes: str


class TriageOutput(BaseModel):
    is_relevant: bool
    urgency: int = Field(ge=1, le=10)


class AnalysisOutput(BaseModel):
    is_novel: bool
    novelty_score: int = Field(ge=1, le=10)
    wow_factor: str
    confidence_label: str
    summary_markdown: str
    needs_human_verification: bool = False
    claims: list[ClaimModel] = Field(default_factory=list)
    citations: list[list[CitationModel]] = Field(default_factory=list)
    protocols: list[ProtocolModel] = Field(default_factory=list)


class VerificationOutput(BaseModel):
    passed: bool
    contradiction_risk: Literal["low", "medium", "high"]
    notes: list[str] = Field(default_factory=list)


class LLMRunIn(BaseModel):
    document_id: int
    stage: LLMStage
    provider: str
    model: str
    prompt_version: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    raw_response_json: dict = Field(default_factory=dict)


class DocumentStatusTransition(BaseModel):
    current: DocumentStatus
    target: DocumentStatus
