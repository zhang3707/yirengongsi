"""Agent registry inside a workspace: create, bind skills, select candidates."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import Agent


class AgentRegistry:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, workspace: str | None = None, status: str = "active") -> list[Agent]:
        stmt = select(Agent)
        if status:
            stmt = stmt.where(Agent.status == status)
        stmt = stmt.order_by(Agent.name)
        return list(self.db.scalars(stmt))

    def get(self, agent_id: str) -> Agent | None:
        return self.db.get(Agent, agent_id)

    def get_by_name(self, name: str) -> Agent | None:
        return self.db.scalar(select(Agent).where(Agent.name == name))

    def create(self, **fields) -> Agent:
        agent = Agent(**fields)
        self.db.add(agent)
        self.db.flush()
        return agent

    def upsert_by_name(self, name: str, **fields) -> Agent:
        agent = self.get_by_name(name)
        if agent is None:
            return self.create(name=name, **fields)
        for key, value in fields.items():
            setattr(agent, key, value)
        self.db.flush()
        return agent

    def candidates_for(self, task_type: str, required_skills: list[str] | None = None) -> list[Agent]:
        required = set(required_skills or [])
        agents = self.list()
        scored: list[tuple[int, Agent]] = []
        for agent in agents:
            score = 0
            skills = set(agent.skills or [])
            if agent.domain == task_type:
                score += 3
            if required and required & skills:
                score += 2 * len(required & skills)
            if agent.domain in {"general", ""}:
                score += 1
            scored.append((score, agent))
        scored.sort(key=lambda item: (-item[0], item[1].name))
        return [agent for _, agent in scored]


registry = AgentRegistry
