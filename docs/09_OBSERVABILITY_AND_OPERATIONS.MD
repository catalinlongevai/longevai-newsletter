# Observability and Operations

## Telemetry

Metrics endpoint: `GET /metrics`

Prometheus metrics include:

- API request count and latency
- Celery task success/failure counters
- LLM stage/provider/model latency histogram

## Tracing

OpenTelemetry instrumentation enabled for:

- FastAPI request lifecycle
- SQLAlchemy DB interactions

## Scheduled Jobs

Defined in `app/tasks/celery_app.py`:

- Source ingestion poll (every 30 minutes)
- Idempotency key cleanup (daily at 02:00)

## Dead-Letter Handling

Failed tasks write into `job_dead_letters` with:

- task name
- payload
- source id (if known)
- retry count
- error text

## Operational Commands

```bash
make run-api
make run-worker
make run-ui
make migrate
make seed
```

## Operational SLO Targets

- Triage p95 <= 8s
- Analysis p95 <= 25s
- Throughput target: 1000 docs/day

Use synthetic load tests and stage telemetry to validate targets.
