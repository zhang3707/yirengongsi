"""Pilot metrics: technical / AI / user indicators from the Pilot monitoring table."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from backend.api.auth import require_token
from backend.api.deps import DbSession
from shared.models import Feedback, Task, TaskEvaluation

router = APIRouter(prefix="/metrics", tags=["metrics"], dependencies=[Depends(require_token)])


@router.get("/pilot")
def pilot_metrics(db: DbSession) -> dict:
    total_tasks = db.scalar(select(func.count()).select_from(Task)) or 0
    succeeded = db.scalar(select(func.count()).select_from(Task).where(Task.status == "succeeded")) or 0
    failed = db.scalar(select(func.count()).select_from(Task).where(Task.status == "failed")) or 0
    running = db.scalar(select(func.count()).select_from(Task).where(Task.status == "running")) or 0

    evaluations = list(db.scalars(select(TaskEvaluation)))
    avg_quality = (
        round(sum(item.quality for item in evaluations) / len(evaluations), 2) if evaluations else 0.0
    )
    avg_experience = (
        round(sum(item.experience for item in evaluations) / len(evaluations), 2)
        if evaluations
        else 0.0
    )
    avg_trust = (
        round(sum(item.trust for item in evaluations) / len(evaluations), 2) if evaluations else 0.0
    )
    avg_saved = (
        round(sum(item.time_saved_ratio for item in evaluations) / len(evaluations), 3)
        if evaluations
        else 0.0
    )
    reusable_ratio = (
        round(sum(1 for item in evaluations if item.reusable) / len(evaluations), 3)
        if evaluations
        else 0.0
    )
    durations = [item.duration_ms for item in db.scalars(select(Task)) if item.duration_ms]
    avg_duration_ms = round(sum(durations) / len(durations), 1) if durations else 0.0

    feedback_counts = {
        category: count
        for category, count in db.execute(
            select(Feedback.category, func.count()).group_by(Feedback.category)
        ).all()
    }

    return {
        "technical": {
            "total_tasks": total_tasks,
            "succeeded": succeeded,
            "failed": failed,
            "running": running,
            "task_success_rate": round(succeeded / total_tasks, 3) if total_tasks else 0.0,
            "average_duration_ms": avg_duration_ms,
        },
        "ai": {
            "evaluations": len(evaluations),
            "average_quality": avg_quality,
            "average_experience": avg_experience,
            "average_trust": avg_trust,
            "average_time_saved_ratio": avg_saved,
            "reusable_ratio": reusable_ratio,
        },
        "feedback": {
            "total": sum(feedback_counts.values()),
            "by_category": feedback_counts,
        },
    }


@router.get("/activity")
def recent_activity(db: DbSession, limit: int = 20) -> list[dict]:
    stmt = select(Task).order_by(Task.created_at.desc()).limit(min(limit, 100))
    return [
        {
            "task_id": task.id,
            "title": task.title,
            "task_type": task.task_type,
            "status": task.status,
            "duration_ms": task.duration_ms,
            "created_at": task.created_at.isoformat(),
        }
        for task in db.scalars(stmt)
    ]
