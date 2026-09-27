"""Skill management endpoints (Console: Skill Management)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from backend.api.auth import require_token
from backend.api.deps import DbSession
from shared.logging import get_logger
from shared.models import Skill
from shared.schemas import SkillCreate, SkillRead, SkillRunRequest, SkillRunResponse
from skill_runtime.executor import SkillExecutionError, SkillExecutor
from skill_runtime.registry import registry

router = APIRouter(prefix="/skills", tags=["skills"], dependencies=[Depends(require_token)])
logger = get_logger("skill")


@router.get("", response_model=list[SkillRead])
def list_skills(db: DbSession) -> list[SkillRead]:
    rows = db.scalars(select(Skill).order_by(Skill.name)).all()
    return [SkillRead.model_validate(row) for row in rows]


@router.post("", response_model=SkillRead, status_code=201)
def create_skill(payload: SkillCreate, db: DbSession) -> SkillRead:
    existing = db.scalar(select(Skill).where(Skill.name == payload.name))
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"skill already exists: {payload.name}")

    row = Skill(**payload.model_dump())
    row.handler = payload.handler or ""
    db.add(row)
    db.flush()
    db.commit()
    return SkillRead.model_validate(row)


@router.post("/{skill_name}/test", response_model=SkillRunResponse)
def test_skill(skill_name: str, payload: SkillRunRequest, db: DbSession) -> SkillRunResponse:
    if payload.skill != skill_name:
        raise HTTPException(status_code=400, detail="skill name mismatch")
    if not registry.has(skill_name):
        raise HTTPException(status_code=404, detail=f"skill not registered: {skill_name}")
    try:
        output, duration_ms = SkillExecutor().execute(skill_name, payload.inputs)
    except SkillExecutionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SkillRunResponse(skill=skill_name, output=output, duration_ms=duration_ms)


@router.get("/registry", response_model=list[str])
def list_registered() -> list[str]:
    return registry.names()
