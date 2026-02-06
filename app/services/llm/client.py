import json
from time import perf_counter
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.observability import LLM_LATENCY
from app.schemas.common import AnalysisOutput, TriageOutput, VerificationOutput
from app.services.llm.prompts import (
    ANALYSIS_PROMPT,
    ANALYSIS_PROMPT_VERSION,
    TRIAGE_PROMPT,
    TRIAGE_PROMPT_VERSION,
    VERIFICATION_PROMPT,
    VERIFICATION_PROMPT_VERSION,
    prompt_checksum,
)
from app.services.llm.router import ModelSelection, stage_candidates

try:
    from openai import AsyncOpenAI
except Exception:  # noqa: BLE001
    AsyncOpenAI = None  # type: ignore[misc,assignment]

try:
    import anthropic as anthropic_sdk
except Exception:  # noqa: BLE001
    anthropic_sdk = None  # type: ignore[assignment]


class LLMTransientError(RuntimeError):
    pass


class LLMSchemaError(RuntimeError):
    pass


def _coerce_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMSchemaError(f"Invalid JSON response: {exc}") from exc


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(LLMTransientError),
    reraise=True,
)
async def _call_openai(model: str, prompt: str, text: str) -> dict:
    settings = get_settings()
    if AsyncOpenAI is None or not settings.openai_api_key:
        raise LLMTransientError("OpenAI client unavailable")

    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
    started = perf_counter()
    try:
        result = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception as exc:  # noqa: BLE001
        raise LLMTransientError(str(exc)) from exc
    latency_ms = int((perf_counter() - started) * 1000)

    message = result.choices[0].message.content or "{}"
    parsed = _coerce_json(message)
    usage = result.usage
    return {
        "provider": "openai",
        "model": model,
        "raw": parsed,
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "latency_ms": latency_ms,
        "cost_usd": None,
    }


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(LLMTransientError),
    reraise=True,
)
async def _call_anthropic(model: str, prompt: str, text: str) -> dict:
    settings = get_settings()
    if anthropic_sdk is None or not settings.anthropic_api_key:
        raise LLMTransientError("Anthropic client unavailable")

    client = anthropic_sdk.AsyncAnthropic(
        api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds
    )
    started = perf_counter()
    try:
        result = await client.messages.create(
            model=model,
            max_tokens=1200,
            temperature=0,
            system=prompt,
            messages=[{"role": "user", "content": text}],
        )
    except Exception as exc:  # noqa: BLE001
        raise LLMTransientError(str(exc)) from exc
    latency_ms = int((perf_counter() - started) * 1000)

    content = ""
    if result.content:
        text_blocks = [getattr(block, "text", "") for block in result.content]
        content = "\n".join([block for block in text_blocks if block])
    parsed = _coerce_json(content)
    usage = getattr(result, "usage", None)
    return {
        "provider": "anthropic",
        "model": model,
        "raw": parsed,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "latency_ms": latency_ms,
        "cost_usd": None,
    }


async def _call_candidate(stage: str, candidate: ModelSelection, prompt: str, text: str) -> dict:
    if candidate.provider == "openai":
        return await _call_openai(candidate.model, prompt, text)
    if candidate.provider == "anthropic":
        return await _call_anthropic(candidate.model, prompt, text)

    raw: Any
    if stage == "triage":
        raw = TriageOutput(is_relevant=("longevity" in text.lower() or "aging" in text.lower()), urgency=5)
    elif stage == "analysis":
        raw = AnalysisOutput(
            is_novel=True,
            novelty_score=6,
            wow_factor="Potentially meaningful finding pending editorial verification.",
            confidence_label="medium",
            summary_markdown="- Preliminary longevity-relevant result detected.",
            needs_human_verification=True,
        )
    else:
        raw = VerificationOutput(passed=True, contradiction_risk="low", notes=[])

    return {
        "provider": candidate.provider,
        "model": candidate.model,
        "raw": raw.model_dump(),
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 1,
        "cost_usd": 0.0,
    }


async def _run_stage(stage: str, prompt: str, prompt_version: str, text: str, parser):
    errors: list[str] = []
    for candidate in stage_candidates(stage):
        try:
            payload = await _call_candidate(stage, candidate, prompt, text)
            output = parser.model_validate(payload["raw"])
            LLM_LATENCY.labels(stage, payload["provider"], payload["model"]).observe(
                (payload.get("latency_ms") or 0) / 1000
            )
            payload["prompt_version"] = prompt_version
            payload["prompt_checksum"] = prompt_checksum(prompt_version)
            return output, payload
        except LLMSchemaError as exc:
            errors.append(f"{candidate.provider}:{candidate.model}:schema:{exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{candidate.provider}:{candidate.model}:error:{exc}")
            continue

    raise RuntimeError(f"No model candidate succeeded for {stage}: {' | '.join(errors)}")


async def run_triage(text: str) -> tuple[TriageOutput, dict]:
    return await _run_stage("triage", TRIAGE_PROMPT, TRIAGE_PROMPT_VERSION, text, TriageOutput)


async def run_analysis(text: str) -> tuple[AnalysisOutput, dict]:
    return await _run_stage(
        "analysis", ANALYSIS_PROMPT, ANALYSIS_PROMPT_VERSION, text, AnalysisOutput
    )


async def run_verification(text: str) -> tuple[VerificationOutput, dict]:
    return await _run_stage(
        "verification", VERIFICATION_PROMPT, VERIFICATION_PROMPT_VERSION, text, VerificationOutput
    )
