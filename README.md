# LongevAI Newsletter

Production-focused MVP scaffold for longevity intelligence ingestion, LLM analysis, editorial review, and Beehiiv draft publishing.

## Stack

- API: FastAPI + Pydantic v2 + SQLAlchemy 2
- Workers: Celery + Redis
- DB: PostgreSQL 16 (pgvector image)
- UI: Streamlit
- Observability: OpenTelemetry + Prometheus metrics endpoint

## Quickstart

```bash
cp .env.example .env
make install
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- Streamlit: `http://localhost:8501`
- Prometheus metrics: `http://localhost:8000/metrics`

## Auth

Write endpoints require:
- `X-API-Key`
- `Idempotency-Key`

## API (Core)

- `GET /v1/sources`
- `POST /v1/sources`
- `PATCH /v1/sources/{id}`
- `POST /v1/manual-ingest`
- `POST /v1/ingest/run`
- `GET /v1/tasks/{id}`
- `GET /v1/inbox`
- `GET /v1/insights/{id}`
- `POST /v1/insights/{id}/approve`
- `POST /v1/insights/{id}/reject`
- `PATCH /v1/insights/{id}`
- `POST /v1/bundles/build`
- `POST /v1/bundles/{id}/publish/beehiiv`
- `GET /v1/metrics/pipeline`

Responses use envelope shape:

```json
{
  "data": {},
  "error": null,
  "meta": {}
}
```

## Development Commands

```bash
make test
make lint
make typecheck
make migrate
make seed
# Optional: enforce only catalog-defined sources
API_AUTH_TOKEN=dev-token .venv/bin/python scripts/seed_sources.py --disable-unmanaged
```

## Documentation

Comprehensive project documentation is available under `docs/`:

- `docs/00_INDEX.MD`
- `docs/01_SETUP_AND_BOOTSTRAP.MD`
- `docs/02_CONFIGURATION.MD`
- `docs/03_ARCHITECTURE.MD`
- `docs/04_DATA_MODEL_AND_MIGRATIONS.MD`
- `docs/05_API_REFERENCE.MD`
- `docs/06_INGESTION_PIPELINE.MD`
- `docs/07_LLM_PIPELINE.MD`
- `docs/08_EDITORIAL_AND_PUBLISHING.MD`
- `docs/09_OBSERVABILITY_AND_OPERATIONS.MD`
- `docs/10_TESTING_AND_QUALITY.MD`
- `docs/11_RELEASE_RUNBOOK.MD`
- `docs/12_TROUBLESHOOTING.MD`
- `docs/13_SOURCE_CATALOG_AND_ONBOARDING.MD`
