from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def record_audit(db: Session, actor: str, action: str, entity_type: str, entity_id: int, payload: dict) -> None:
    db.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload,
        )
    )
