"""Health endpoint: reports service, database and Redis status."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from shared.config import settings
from shared.schemas import HealthResponse

router = APIRouter(tags=["health"])

VERSION = "1.0.0"


def _check_database() -> str:
    from shared.database import SessionLocal

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return f"error: {exc.__class__.__name__}"


def _check_redis() -> str:
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return "ok"
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return f"unavailable: {exc.__class__.__name__}"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database = _check_database()
    redis_state = _check_redis()
    services = {
        "api_gateway": "ok",
        "agent_runtime": "ok",
        "skill_runtime": "ok",
        "workflow_engine": "ok",
        "knowledge_service": "ok",
        "database": database,
        "redis": redis_state,
        "temporal": "external",
        "console": "ok",
    }
    overall = "ok" if database == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        environment=settings.environment,
        version=VERSION,
        database=database,
        redis=redis_state,
        services=services,
    )
