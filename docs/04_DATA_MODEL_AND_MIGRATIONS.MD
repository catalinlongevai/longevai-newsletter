# Data Model and Migrations

## Core Tables

- `sources`: source config and operational health fields
- `raw_documents`: immutable fetched snapshots
- `documents`: normalized document and processing status
- `document_duplicates`: dedupe relationships
- `llm_runs`: stage-level model telemetry and raw output
- `insights`: editorially relevant extracted insight records
- `claims`, `citations`, `protocols`: structured extraction artifacts
- `publish_bundles`: generated draft bundles and publish metadata
- `audit_logs`: actor/action trace
- `idempotency_keys`: write request dedupe and replay cache
- `job_dead_letters`: failed task payloads
- `pipeline_metrics_daily`: daily pipeline counters

## Status Lifecycle

`ingested -> triaged -> analyzed -> verified -> ready_for_review -> approved|rejected -> bundled -> published`

Status transitions are enforced in shared state-machine logic.

## Migrations

- Alembic config: `alembic.ini`
- Migration environment: `alembic/env.py`
- Initial migration: `alembic/versions/0001_initial.py`

## Migration Commands

```bash
make migrate
```

or

```bash
.venv/bin/alembic upgrade head
```

## Indexes and Constraints

- Composite idempotency uniqueness: `(key, endpoint)`
- `llm_runs(document_id, stage)`
- Source activity index: `(active, method)`
- Bundle period index: `(period_start, period_end)`
- Document status index

## Notes

- The initial migration contains explicit operations and deterministic downgrade paths.
- `pgvector` extension is enabled on PostgreSQL dialects.
