import os

from app.core.config import get_settings
from app.services.llm.router import stage_candidates


def test_stage_candidates_stub_when_no_keys():
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["ANTHROPIC_API_KEY"] = ""
    get_settings.cache_clear()
    candidates = stage_candidates("analysis")
    assert candidates[0].provider == "stub"


def test_stage_candidates_prefers_openai_triage_when_set():
    os.environ["OPENAI_API_KEY"] = "x"
    os.environ["ANTHROPIC_API_KEY"] = ""
    get_settings.cache_clear()
    candidates = stage_candidates("triage")
    assert candidates[0].provider == "openai"
