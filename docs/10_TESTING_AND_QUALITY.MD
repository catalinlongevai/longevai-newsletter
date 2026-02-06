# Testing and Quality

## Quality Gates

- `ruff` must pass
- `mypy` must pass
- `pytest` must pass
- Alembic migration smoke test must pass
- Docker build smoke test must pass

## Local Commands

```bash
make lint
make typecheck
make test
```

## Test Structure

- `tests/unit`: focused logic tests
- `tests/integration`: API contract and flow tests

## Covered Areas (Current)

- State transition rules
- Schema validation
- Idempotency behavior including conflict
- API envelope/error behavior
- Task polling endpoint
- Network safety basics
- DOI extraction utility
- Router selection behavior

## Recommended Additions

- Full provider mock tests for OpenAI/Anthropic failure matrix
- End-to-end ingest -> verify flow with mocked external services
- Beehiiv publish contract tests (success/failure payloads)
- Load test scripts for 1000 docs/day target
