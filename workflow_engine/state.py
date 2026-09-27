"""Workflow step state helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_SUCCEEDED = "succeeded"
STEP_FAILED = "failed"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_step(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": STEP_PENDING,
        "started_at": None,
        "finished_at": None,
        "detail": {},
        "error": None,
    }


def mark_running(step: dict[str, Any]) -> dict[str, Any]:
    step["status"] = STEP_RUNNING
    step["started_at"] = now_iso()
    return step


def mark_succeeded(step: dict[str, Any], detail: dict[str, Any] | None = None) -> dict[str, Any]:
    step["status"] = STEP_SUCCEEDED
    step["finished_at"] = now_iso()
    if detail:
        step["detail"] = detail
    return step


def mark_failed(step: dict[str, Any], error: str) -> dict[str, Any]:
    step["status"] = STEP_FAILED
    step["finished_at"] = now_iso()
    step["error"] = error
    return step
