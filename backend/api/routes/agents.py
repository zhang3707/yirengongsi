"""Agent management endpoints (Console: Agent Management)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agent_runtime.registry import AgentRegistry
from backend.api.auth import require_token
from backend.api.deps import DbSession
from shared.events import record_event
from shared.schemas import AgentCreate, AgentRead

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(require_token)])


@router.get("", response_model=list[AgentRead])
def list_agents(db: DbSession) -> list[AgentRead]:
    return [AgentRead.model_validate(agent) for agent in AgentRegistry(db).list()]


@router.post("", response_model=AgentRead, status_code=201)
def create_agent(payload: AgentCreate, db: DbSession) -> AgentRead:
    registry = AgentRegistry(db)
    if registry.get_by_name(payload.name):
        raise HTTPException(status_code=409, detail=f"agent already exists: {payload.name}")
    agent = registry.create(**payload.model_dump())
    record_event(db, "agent.created", service="agent", message=agent.name, context={"agent_id": agent.id})
    db.commit()
    return AgentRead.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, db: DbSession) -> AgentRead:
    agent = AgentRegistry(db).get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return AgentRead.model_validate(agent)
