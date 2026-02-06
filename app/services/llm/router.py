from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class ModelSelection:
    provider: str
    model: str


def stage_candidates(stage: str) -> list[ModelSelection]:
    settings = get_settings()
    candidates: list[ModelSelection] = []

    if stage == "triage":
        if settings.openai_api_key:
            candidates.append(ModelSelection(provider="openai", model="gpt-4.1-mini"))
        if settings.anthropic_api_key:
            candidates.append(ModelSelection(provider="anthropic", model="claude-3-5-haiku-latest"))
    elif stage == "analysis":
        if settings.anthropic_api_key:
            candidates.append(ModelSelection(provider="anthropic", model="claude-sonnet-4-5"))
        if settings.openai_api_key:
            candidates.append(ModelSelection(provider="openai", model="gpt-5"))
    elif stage == "verification":
        if settings.openai_api_key:
            candidates.append(ModelSelection(provider="openai", model="gpt-5-mini"))
        if settings.anthropic_api_key:
            candidates.append(ModelSelection(provider="anthropic", model="claude-3-5-haiku-latest"))

    if not candidates:
        candidates.append(ModelSelection(provider="stub", model="stub-v1"))
    return candidates


def select_model(stage: str) -> ModelSelection:
    return stage_candidates(stage)[0]
