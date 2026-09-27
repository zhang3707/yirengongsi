"""Pilot Feedback Pool endpoints (bug / usability / ai_quality / workflow / feature_request / business_value)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from backend.api.auth import require_token
from backend.api.deps import DbSession
from shared.events import record_event
from shared.models import Feedback
from shared.schemas import FeedbackCreate, FeedbackRead

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(require_token)])

# Priority = Impact x Frequency (Pilot doc), mapped to P0-P3.
_LEVEL = {"high": 3, "medium": 2, "low": 1}


def compute_priority(impact: str, frequency: str) -> str:
    score = _LEVEL.get(impact.lower(), 2) * _LEVEL.get(frequency.lower(), 2)
    if score >= 9:
        return "P0"
    if score >= 6:
        return "P1"
    if score >= 3:
        return "P2"
    return "P3"


@router.get("", response_model=list[FeedbackRead])
def list_feedback(db: DbSession, category: str | None = None, limit: int = 100) -> list[FeedbackRead]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).limit(min(limit, 500))
    if category:
        stmt = stmt.where(Feedback.category == category)
    return [FeedbackRead.model_validate(row) for row in db.scalars(stmt)]


@router.post("", response_model=FeedbackRead, status_code=201)
def create_feedback(payload: FeedbackCreate, db: DbSession) -> FeedbackRead:
    priority = compute_priority(payload.impact, payload.frequency)
    entry = Feedback(
        category=payload.category,
        summary=payload.summary,
        scenario=payload.scenario,
        impact=payload.impact or "medium",
        frequency=payload.frequency or "medium",
        suggestion=payload.suggestion,
        task_id=payload.task_id,
        reporter=payload.reporter,
        priority=priority,
    )
    db.add(entry)
    db.flush()
    record_event(
        db,
        "feedback.created",
        service="backend",
        message=payload.summary,
        context={"category": payload.category, "priority": priority},
    )
    db.commit()
    return FeedbackRead.model_validate(entry)
