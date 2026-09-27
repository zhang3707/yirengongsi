"""Agent runtime: resolve the skill chain for a task and expose agent execution.

The runtime deliberately keeps orchestration in the workflow engine (see
`workflow_engine.steps`) so the doc's step order stays in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from agent_runtime.selector import AgentSelector, SelectionResult
from shared.logging import get_logger
from shared.models import Agent, Task
from skill_runtime.registry import registry as skill_registry

logger = get_logger("agent")

# Documented test scenarios -> skill chain used by the default workflow.
TASK_TYPE_SKILL_CHAIN: dict[str, list[str]] = {
    "research": ["search", "analysis", "report"],
    "analysis": ["analysis", "report"],
    "content": ["content", "report"],
    "workflow": ["analysis", "report"],
    "general": ["analysis", "report"],
}


@dataclass(slots=True)
class AgentExecutionResult:
    agent: Agent
    selection: SelectionResult
    skill_chain: list[str] = field(default_factory=list)


class AgentRuntime:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = AgentRegistry(db)
        self.selector = AgentSelector(self.registry)

    def resolve_skill_chain(self, task_type: str, agent: Agent) -> list[str]:
        """Resolve the ordered skill chain for this agent.

        Rules:
          * an agent with no declared skills uses the default chain for the task type;
          * an agent with declared skills only runs what it declares, keeping the
            documented order where possible;
          * declared skills the runtime cannot resolve are *kept* in the chain so
            the Skill Execute step fails loudly instead of silently degrading.
        """
        preferred = TASK_TYPE_SKILL_CHAIN.get(task_type, TASK_TYPE_SKILL_CHAIN["general"])
        declared = list(dict.fromkeys(agent.skills or []))

        if not declared:
            chain = list(preferred)
        else:
            ordered = [skill for skill in preferred if skill in declared]
            extra = [skill for skill in declared if skill not in preferred]
            chain = ordered + extra

        unknown = [skill for skill in chain if not skill_registry.has(skill)]
        if unknown:
            logger.warning(
                "agent %s declares skills not registered in the runtime: %s", agent.name, unknown
            )
        return chain

    def prepare(self, task: Task) -> AgentExecutionResult:
        if task.assigned_agent_id:
            agent = self.registry.get(task.assigned_agent_id)
            if agent is None:
                raise LookupError(f"assigned agent not found: {task.assigned_agent_id}")
            selection = SelectionResult(agent=agent, score=0, reason="pre-assigned")
        else:
            selection = self.selector.select(task_type=task.task_type)
            agent = selection.agent
            task.assigned_agent_id = agent.id
            self.db.flush()

        chain = self.resolve_skill_chain(task.task_type, agent)
        logger.info("agent %s prepared for task %s with chain %s", agent.name, task.id, chain)
        return AgentExecutionResult(agent=agent, selection=selection, skill_chain=chain)
