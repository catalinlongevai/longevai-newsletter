import pytest

from app.models.entities import DocumentStatus
from app.state_machine.document_status import can_transition, enforce_transition


def test_valid_transition_chain():
    assert can_transition(DocumentStatus.ingested, DocumentStatus.triaged)
    assert can_transition(DocumentStatus.ready_for_review, DocumentStatus.approved)
    assert can_transition(DocumentStatus.ingested, DocumentStatus.rejected)


def test_invalid_transition_raises():
    with pytest.raises(ValueError):
        enforce_transition(DocumentStatus.ingested, DocumentStatus.published)
    with pytest.raises(ValueError):
        enforce_transition(DocumentStatus.approved, DocumentStatus.rejected)
