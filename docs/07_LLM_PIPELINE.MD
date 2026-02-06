# LLM Pipeline

The LLM layer has 3 stages and provider fallback support.

## Stages

1. `triage`
2. `analysis`
3. `verification`

## Model Routing

File: `app/services/llm/router.py`

Per-stage candidate list is built from available provider keys.

- Triage: OpenAI mini then Anthropic haiku
- Analysis: Anthropic sonnet then OpenAI
- Verification: OpenAI mini then Anthropic haiku
- No keys: stub fallback

## Prompt Management

Files:

- `app/services/llm/prompts.py`
- `app/services/llm/prompt_templates/*.txt`

Prompt versions and checksums are attached to run metadata.

## Provider Clients

File: `app/services/llm/client.py`

- OpenAI async client path
- Anthropic async client path
- Strict JSON parsing and schema validation
- Retry only on transient failures
- Fallback across providers when candidates fail

## Guardrails

- Schema-first outputs (Pydantic validation)
- Verification stage can reject content
- Protocol extraction enforces dose/safety requirements
- Insights marked with `needs_human_verification` are not auto-approvable

## Telemetry

Persisted in `llm_runs`:

- provider
- model
- prompt_version
- token counts
- latency
- raw response payload
