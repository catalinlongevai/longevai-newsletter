# Release Runbook

This runbook describes the MVP release sequence.

## Pre-Release Checklist

1. Run `make lint`, `make typecheck`, `make test`.
2. Confirm `.env` production secrets are loaded from secret manager.
3. Run migrations in staging.
4. Run one full ingestion + editorial + publish dry run in staging.
5. Verify metrics and trace visibility.

## Deployment Sequence

1. Build and push container image.
2. Deploy API.
3. Deploy worker.
4. Deploy scheduler.
5. Deploy UI.
6. Run migration job.
7. Execute smoke checks:
   - `GET /healthz`
   - `GET /v1/sources`
   - `GET /v1/metrics/pipeline`

## First Production Cycle

1. Seed production sources.
2. Trigger ingestion once manually.
3. Verify queue/task progression.
4. Review inbox and approve a small set.
5. Build bundle.
6. Publish Beehiiv draft.

## Rollback

1. Roll back application image to last stable tag.
2. If schema is incompatible, apply matching DB rollback migration.
3. Re-run smoke checks.

## Post-Release Monitoring (First 24h)

- Task failure rate
- Dead-letter entries
- API error rate
- LLM timeout or schema failure frequency
- Publish error rate
