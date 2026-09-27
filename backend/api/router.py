"""Aggregate API router."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.routes import (
    agents,
    feedback,
    health,
    knowledge,
    metrics,
    skills,
    tasks,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(skills.router)
api_router.include_router(tasks.router)
api_router.include_router(workflows.router)
api_router.include_router(knowledge.router)
api_router.include_router(feedback.router)
api_router.include_router(metrics.router)
