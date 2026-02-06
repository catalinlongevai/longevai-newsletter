# API Reference

Base URL: `http://localhost:8000`

## Authentication and Idempotency

Write endpoints require:

- `X-API-Key: <token>`
- `Idempotency-Key: <unique-key>`

## Envelope Contract

All responses use:

```json
{
  "data": {},
  "error": null,
  "meta": {}
}
```

On failure, `error` is populated with `code`, `message`, `trace_id`, and optional `details`.

## Endpoints

### Source Management

- `GET /v1/sources`
- `POST /v1/sources`
- `PATCH /v1/sources/{id}`

### Ingestion and Tasks

- `POST /v1/manual-ingest`
- `POST /v1/ingest/run`
- `GET /v1/tasks/{id}`

### Inbox and Insight Review

- `GET /v1/inbox`
- `GET /v1/insights/{id}`
- `POST /v1/insights/{id}/approve`
- `POST /v1/insights/{id}/reject`
- `PATCH /v1/insights/{id}`

### Document Transition

- `POST /v1/documents/{id}/transition`

### Bundling and Publishing

- `POST /v1/bundles/build`
- `POST /v1/bundles/{id}/publish/beehiiv`

### Metrics

- `GET /v1/metrics/pipeline`
- `GET /metrics`

## Example: Create Source

```bash
curl -X POST http://localhost:8000/v1/sources \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-token' \
  -H 'Idempotency-Key: source-001' \
  -d '{
    "name":"PubMed Longevity",
    "method":"pubmed",
    "config_json":{"pubmed_query":"(longevity OR aging)"},
    "active":true,
    "poll_interval_min":60,
    "trust_tier":"standard"
  }'
```

## Example: Filter Inbox

`GET /v1/inbox?status=ready_for_review&min_novelty=6&order=desc`
