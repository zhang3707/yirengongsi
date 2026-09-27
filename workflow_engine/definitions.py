"""Workflow definitions. The Pilot runbook fixes the default step order:

Task Receive -> Agent Select -> Skill Execute -> Result Generate -> Save Record
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkflowDefinition:
    name: str
    description: str
    steps: list[str]
    retry_step: str = "skill_execute"
    metadata: dict = field(default_factory=dict)


WORKFLOW_STEPS = [
    "task_receive",
    "agent_select",
    "skill_execute",
    "result_generate",
    "save_record",
]

STEP_LABELS = {
    "task_receive": "Task Receive",
    "agent_select": "Agent Select",
    "skill_execute": "Skill Execute",
    "result_generate": "Result Generate",
    "save_record": "Save Record",
}

DEFAULT_WORKFLOW = WorkflowDefinition(
    name="default",
    description="Pilot 默认闭环：接收任务 → 选择 Agent → 执行 Skill → 生成结果 → 记录归档。",
    steps=list(WORKFLOW_STEPS),
)

WORKFLOWS: dict[str, WorkflowDefinition] = {DEFAULT_WORKFLOW.name: DEFAULT_WORKFLOW}


def get_workflow(name: str) -> WorkflowDefinition:
    return WORKFLOWS.get(name, DEFAULT_WORKFLOW)


def list_workflows() -> list[WorkflowDefinition]:
    return list(WORKFLOWS.values())
