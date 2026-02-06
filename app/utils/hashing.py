import hashlib
import json


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_request_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_text(body)
