"""Minimal single-tenant API authentication (Local MVP — see AGENTS.md §2).

Phase=Local MVP: 保持默认关闭。这个 token 只用来满足"本地或内网很快能开认证"的
一致性，不引入用户/租户/注册/计费/多租户等冻结项。
若 `API_AUTH_TOKEN` 非空（或 `API_AUTH_ENABLED=true`）则保护业务路由；
`/health`、`/console/`、`/docs` 与 `GET /api/v1/workflows` 公开。
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
