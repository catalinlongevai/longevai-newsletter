from pathlib import Path

from app.utils.hashing import sha256_text

PROMPT_DIR = Path(__file__).resolve().parent / "prompt_templates"

TRIAGE_PROMPT_VERSION = "triage_v1"
ANALYSIS_PROMPT_VERSION = "analysis_v1"
VERIFICATION_PROMPT_VERSION = "verification_v1"


def _load_prompt(version: str) -> str:
    path = PROMPT_DIR / f"{version}.txt"
    return path.read_text(encoding="utf-8").strip()


def prompt_for(version: str) -> str:
    return _load_prompt(version)


def prompt_checksum(version: str) -> str:
    return sha256_text(prompt_for(version))


TRIAGE_PROMPT = prompt_for(TRIAGE_PROMPT_VERSION)
ANALYSIS_PROMPT = prompt_for(ANALYSIS_PROMPT_VERSION)
VERIFICATION_PROMPT = prompt_for(VERIFICATION_PROMPT_VERSION)
