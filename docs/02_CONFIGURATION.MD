# Configuration

Configuration is loaded via `app/core/config.py` using environment variables.

## Core Runtime

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_EAGER_MODE`

## API and Security

- `API_AUTH_ENABLED`
- `API_AUTH_TOKEN`
- `ALLOWED_FETCH_HOSTS`

If `API_AUTH_ENABLED=true`, requests to write endpoints must include `X-API-Key`.

## LLM Flags and Provider Keys

- `LLM_ENABLED`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Behavior:

- If `LLM_ENABLED=true`, at least one provider key must be configured.
- If both are configured, provider selection and fallback are stage-based.

## PubMed

- `NCBI_API_KEY`

If set, PubMed requests include API key and can handle larger throughput.

## Beehiiv Publishing

- `BEEHIIV_ENABLED`
- `BEEHIIV_API_KEY`
- `BEEHIIV_PUBLICATION_ID`

If disabled or unconfigured, publish endpoint returns a skipped response.

## Validation Rules (Important)

Settings validation enforces:

- Missing API auth token when auth is enabled causes startup failure.
- Missing Beehiiv keys when Beehiiv feature is enabled causes startup failure.
- Missing both LLM provider keys when LLM feature is enabled causes startup failure.

## Recommended Local Values

```env
API_AUTH_ENABLED=true
API_AUTH_TOKEN=dev-token
LLM_ENABLED=false
BEEHIIV_ENABLED=false
ALLOWED_FETCH_HOSTS=
```

## Production Notes

- Keep secrets in managed secret store.
- Do not commit `.env`.
- Restrict `ALLOWED_FETCH_HOSTS` to approved source domains.
