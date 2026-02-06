from app.models.entities import DocumentStatus


_ALLOWED = {
    DocumentStatus.ingested: {DocumentStatus.triaged, DocumentStatus.rejected},
    DocumentStatus.triaged: {DocumentStatus.analyzed, DocumentStatus.rejected},
    DocumentStatus.analyzed: {DocumentStatus.verified, DocumentStatus.rejected},
    DocumentStatus.verified: {DocumentStatus.ready_for_review, DocumentStatus.rejected},
    DocumentStatus.ready_for_review: {DocumentStatus.approved, DocumentStatus.rejected},
    DocumentStatus.approved: {DocumentStatus.bundled},
    DocumentStatus.bundled: {DocumentStatus.published},
    DocumentStatus.rejected: set(),
    DocumentStatus.published: set(),
}


def can_transition(current: DocumentStatus, target: DocumentStatus) -> bool:
    return target in _ALLOWED[current]


def enforce_transition(current: DocumentStatus, target: DocumentStatus) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Invalid document transition: {current} -> {target}")
