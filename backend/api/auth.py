"""Minimal single-tenant API authentication.

Token auth is OFF by default. Set `API_AUTH_TOKEN` (and optionally `API_AUTH_ENABLED=true`)
to protect all business routes; `/health`, `/console/`, OpenAPI docs and `GET /api/v1/workflows`
remain public because they expose no business data and the Console needs them to boot.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from shared.config import settings


def auth_token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-API-Token") or None


def require_token(request: Request) -> None:
    enabled = (settings.api_auth_enabled or bool(settings.api_auth_token)) if hasattr(
        settings, "api_auth_enabled"
    ) else bool(settings.api_auth_token)
    if not enabled:
        return
    token = auth_token_from_request(request)
    if token != settings.api_auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
