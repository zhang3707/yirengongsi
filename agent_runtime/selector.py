"""Agent selection: pick the best agent for a task, per the runbook "Agent Select" step."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_runtime.registry import AgentRegistry
from shared.models import Agent


@dataclass(slots=True)
class SelectionResult:
    agent: Agent
    score: int
    matched_skills: list[str] = field(default_factory=list)
    reason: str = ""


class AgentSelector:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def select(self, *, task_type: str, skills: list[str] | None = None) -> SelectionResult:
        candidates = self.registry.candidates_for(task_type, skills)
        if not candidates:
            raise LookupError("no active agent available for task")

        agent = candidates[0]
        matched = sorted(set(skills or []) & set(agent.skills or []))
        score = (3 if agent.domain == task_type else 0) + 2 * len(matched)
        reason = f"domain={agent.domain} matches task_type={task_type}"
        if matched:
            reason += f"; matched skills={matched}"
        return SelectionResult(agent=agent, score=score, matched_skills=matched, reason=reason)
