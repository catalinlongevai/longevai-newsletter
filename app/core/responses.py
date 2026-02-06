from typing import Any


def success_response(data: Any, meta: dict | None = None) -> dict:
    return {
        "data": data,
        "error": None,
        "meta": meta or {},
    }


def error_response(code: str, message: str, trace_id: str, status: int = 400, details: dict | None = None) -> tuple[dict, int]:
    return (
        {
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "trace_id": trace_id,
                "details": details or {},
            },
            "meta": {},
        },
        status,
    )
