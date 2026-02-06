# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LongevAI Newsletter is a production MVP for longevity intelligence ingestion, LLM analysis, editorial review, and Beehiiv draft publishing. It's a multi-service ETL and editorial pipeline built with FastAPI, Celery, PostgreSQL (pgvector), Redis, and Streamlit.

**Python 3.12+ required.**

## Common Commands

```bash
# Setup
cp .env.example .env
make install          # Create .venv, install with dev deps

# Run services (all-in-one)
docker compose up --build

# Run individual services
make run-api          # FastAPI dev server (port 8000)
make run-worker       # Celery worker
make run-ui           # Streamlit UI (port 8501)

# Database
make migrate          # Alembic upgrade head
make seed             # Seed initial sources

# Quality
make test             # pytest
make lint             # ruff check
make typecheck        # mypy

# Run specific tests
pytest tests/unit/
pytest tests/integration/
pytest tests/integration/test_api.py::test_create_source_idempotent_replay
```

## Architecture

### Service Topology

- **API** (FastAPI): REST endpoints at `/v1/...`, Swagger at `/docs`
- **Worker** (Celery): Async tasks across queues: ingest, llm, publish, default
- **Scheduler** (Celery Beat): Polls sources every 30min, cleans idempotency keys daily
- **UI** (Streamlit): Editorial control plane with source management, review inbox, bundle publishing, metrics
- **DB**: PostgreSQL 16 with pgvector
- **Broker**: Redis 7

### Request Flow

HTTP → auth middleware (X-API-Key) → Pydantic validation → idempotency check → business logic → Celery task enqueue (or eager execution) → JSON envelope response with X-Trace-Id header.

### Document Lifecycle State Machine

`ingested → triaged → analyzed → verified → ready_for_review → approved → bundled → published`

Any stage can transition to `rejected`. Transitions enforced in `app/state_machine/document_status.py`.

### Ingestion Adapter Pattern

All adapters in `app/services/ingestion/` return `list[IngestedItem]`:
- **RSS**: Feed parsing with ETag/Last-Modified caching
- **PubMed**: NCBI API queries
- **HTML**: Playwright scraping with CSS selectors
- **Manual**: User-submitted text/URL

### LLM Pipeline

Three stages via `app/services/llm/client.py` (supports OpenAI and Anthropic):
1. **Triage**: Relevance classification
2. **Analysis**: Claim/citation/protocol extraction
3. **Verification**: Output quality validation

Includes exponential backoff retry (3 attempts), JSON coercion, latency/cost tracking.

### Key Modules

| Path | Purpose |
|------|---------|
| `app/api/routes.py` | All API endpoints |
| `app/core/config.py` | Pydantic settings with cross-field validation |
| `app/core/auth.py` | X-API-Key authentication dependency |
| `app/core/responses.py` | `success_response()`/`error_response()` envelope helpers |
| `app/models/entities.py` | All SQLAlchemy ORM models |
| `app/schemas/common.py` | Pydantic request/response schemas |
| `app/services/pipeline.py` | Document pipeline orchestration |
| `app/services/idempotency.py` | Idempotency key caching (7-day TTL) |
| `app/tasks/celery_app.py` | Celery config, beat schedule, queue routing |
| `app/tasks/jobs.py` | Celery task definitions |
| `app/utils/hashing.py` | SHA256 content hashing for deduplication |
| `app/utils/network.py` | URL validation against ALLOWED_FETCH_HOSTS |

## API Conventions

- All responses use `{data, error, meta}` envelope format
- Write endpoints (POST/PATCH/PUT/DELETE) require `X-API-Key` and `Idempotency-Key` headers
- Idempotency: same key + same payload = cached replay; same key + different payload = HTTP 409
- `X-Trace-Id` header auto-generated if not provided; included in all error responses
- Audit log records every state change with actor, action, entity, and payload

## Testing

- Tests use SQLite in-memory DB (configured in `tests/conftest.py`)
- Auth disabled in test env (`API_AUTH_ENABLED=false`)
- Celery runs in eager mode (synchronous) during tests
- FastAPI TestClient provided via fixtures

## CI Pipeline (.github/workflows/ci.yml)

Runs on push/PR: ruff check → mypy → pytest → alembic upgrade head → docker build.

## Adding New Features

**New endpoint**: Define schema in `app/schemas/common.py` → add route in `app/api/routes.py` → use `resolve_cached_response()`/`store_response()` for idempotency → return `success_response()`.

**New migration**: Modify `app/models/entities.py` → `alembic revision --autogenerate -m "description"` → review generated file → `make migrate`.

**New Celery task**: Define in `app/tasks/jobs.py` → add queue route in `celery_app.py` → call via `.delay()`.

## Configuration Validation

Settings in `app/core/config.py` enforce:
- API auth token required when `api_auth_enabled=true` (non-test)
- Beehiiv credentials required when `beehiiv_enabled=true`
- At least one LLM provider key required when `llm_enabled=true`
