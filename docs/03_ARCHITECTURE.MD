# Architecture

The system is a multi-service ETL and editorial pipeline.

## Services

- `api` (`FastAPI`): API contracts, auth, response envelope, orchestration endpoints.
- `worker` (`Celery`): ingestion, triage, analysis, verification, cleanup tasks.
- `scheduler` (`Celery Beat`): recurring ingestion and maintenance jobs.
- `db` (`PostgreSQL`): system of record.
- `redis` (`Redis`): Celery broker/result backend.
- `ui` (`Streamlit`): editorial control plane.

## Request and Processing Flow

1. Source is configured via `/v1/sources`.
2. Ingestion is triggered by schedule or `/v1/ingest/run`.
3. Worker fetches data from source-specific adapter.
4. Raw document is upserted and deduplicated.
5. Triage stage classifies relevance.
6. Analysis stage extracts claims/citations/protocols.
7. Verification stage confirms output quality and contradiction risk.
8. Approved insights are bundled and drafted to Beehiiv.

## Cross-Cutting Concerns

- Auth middleware (`X-API-Key`)
- Idempotency key checks for write endpoints
- Structured envelope responses
- OpenTelemetry instrumentation
- Prometheus metrics emission
- Audit logs for editorial and operational changes

## Important Code Entry Points

- API app: `app/main.py`
- API routes: `app/api/routes.py`
- Task graph: `app/tasks/jobs.py`
- DB entities: `app/models/entities.py`
- LLM integration: `app/services/llm`
- Ingestion adapters: `app/services/ingestion`
