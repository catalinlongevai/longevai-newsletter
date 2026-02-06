from datetime import timedelta

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import now_utc
from app.models.entities import IdempotencyKey
from app.utils.hashing import stable_request_hash


IDEMPOTENCY_HEADER = "Idempotency-Key"


def resolve_cached_response(
    db: Session, request: Request, endpoint: str, payload: dict
) -> dict | None:
    key = request.headers.get(IDEMPOTENCY_HEADER)
    if not key:
        raise HTTPException(status_code=400, detail=f"Missing {IDEMPOTENCY_HEADER} header")

    request_hash = stable_request_hash(payload)
    existing = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key == key, IdempotencyKey.endpoint == endpoint)
        .one_or_none()
    )
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key reused with different payload")
        return existing.response_json
    return None


def store_response(db: Session, key: str, endpoint: str, payload: dict, response_json: dict) -> None:
    request_hash = stable_request_hash(payload)
    db.add(
        IdempotencyKey(
            key=key,
            endpoint=endpoint,
            request_hash=request_hash,
            response_json=response_json,
        )
    )


def cleanup_expired_keys(db: Session) -> int:
    settings = get_settings()
    cutoff = now_utc() - timedelta(hours=settings.idempotency_ttl_hours)
    deleted = (
        db.query(IdempotencyKey).filter(IdempotencyKey.created_at < cutoff).delete(synchronize_session=False)
    )
    return deleted
