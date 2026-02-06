# Troubleshooting

## API returns 401 Unauthorized

Cause:

- Missing or incorrect `X-API-Key`.

Fix:

- Set correct `API_AUTH_TOKEN`.
- Send `X-API-Key` header on write requests.

## Write endpoint returns 400 Missing Idempotency-Key

Cause:

- Missing idempotency header.

Fix:

- Add unique `Idempotency-Key` per logical write operation.

## Write endpoint returns 409 Idempotency key reused with different payload

Cause:

- Same key reused with changed request body.

Fix:

- Use a fresh key for changed payloads.

## Ingestion fails with host/protocol errors

Cause:

- URL blocked by SSRF controls.

Fix:

- Ensure URL uses `http`/`https`.
- Add domain to `ALLOWED_FETCH_HOSTS` if allowlist is enabled.

## LLM stage keeps failing

Cause:

- Provider key missing, network error, or schema mismatch.

Fix:

- Check `LLM_ENABLED` and provider keys.
- Inspect `llm_runs` and dead-letter entries.
- Verify prompt template output matches Pydantic schemas.

## Publish returns skipped

Cause:

- `BEEHIIV_ENABLED=false` or missing Beehiiv credentials.

Fix:

- Enable Beehiiv and configure `BEEHIIV_API_KEY` and `BEEHIIV_PUBLICATION_ID`.

## Celery tasks do not progress

Cause:

- Worker not running or Redis unavailable.

Fix:

- Verify `worker` and `redis` services are healthy.
- Check Celery logs for queue binding and errors.

## Migration issues

Cause:

- Database drift or failed prior migration.

Fix:

- Inspect alembic version table.
- Re-run `alembic upgrade head` in clean environment first.
