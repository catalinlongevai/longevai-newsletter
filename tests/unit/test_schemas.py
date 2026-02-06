import pytest
from pydantic import ValidationError

from app.schemas.common import AnalysisOutput


def test_analysis_output_rejects_invalid_novelty():
    with pytest.raises(ValidationError):
        AnalysisOutput(
            is_novel=True,
            novelty_score=99,
            wow_factor="x",
            confidence_label="medium",
            summary_markdown="x",
        )


def test_analysis_output_accepts_minimal_valid():
    out = AnalysisOutput(
        is_novel=True,
        novelty_score=5,
        wow_factor="x",
        confidence_label="medium",
        summary_markdown="x",
    )
    assert out.novelty_score == 5
