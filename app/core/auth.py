from fastapi import HTTPException, Request

from app.core.config import get_settings


AUTH_HEADER = "X-API-Key"


def enforce_api_auth(request: Request) -> None:
    settings = get_settings()
    if not settings.api_auth_enabled:
        return

    token = request.headers.get(AUTH_HEADER)
    if not token or token != settings.api_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
