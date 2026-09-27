"""Concrete step implementations for the default workflow.

Each step receives the mutable run context and returns a detail dict stored on the step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from agent_runtime.runtime import AgentRuntime
from knowledge_service.service import KnowledgeService
from shared.events import record_event
from shared.models import Task, WorkflowRun
from skill_runtime.base import SkillContext
from skill_runtime.executor import SkillExecutor


@dataclass
class RunContext:
    db: Session
    task: Task
    run: WorkflowRun
    payload: dict[str, Any] = field(default_factory=dict)


def task_receive(ctx: RunContext) -> dict[str, Any]:
    ctx.task.status = "running"
    ctx.db.flush()
    record_event(
        ctx.db,
        "task.received",
        service="workflow",
        message=ctx.task.title,
        context={"task_id": ctx.task.id, "task_type": ctx.task.task_type},
    )
    return {"task_id": ctx.task.id, "task_type": ctx.task.task_type}


def agent_select(ctx: RunContext) -> dict[str, Any]:
    prepared = AgentRuntime(ctx.db).prepare(ctx.task)
    ctx.payload["agent"] = prepared.agent
    ctx.payload["skill_chain"] = prepared.skill_chain
    record_event(
        ctx.db,
        "agent.selected",
        service="agent",
        message=prepared.agent.name,
        context={
            "task_id": ctx.task.id,
            "agent_id": prepared.agent.id,
            "reason": prepared.selection.reason,
            "skill_chain": prepared.skill_chain,
        },
    )
    return {
        "agent_id": prepared.agent.id,
        "agent_name": prepared.agent.name,
        "reason": prepared.selection.reason,
        "skill_chain": prepared.skill_chain,
    }


def _merge_step_output(
    current: dict[str, Any], output: dict[str, Any], default_material: Any
) -> dict[str, Any]:
    """Merge a skill's output into the run context safely.

    Generic merging (spread) lets array-typed keys (e.g. `analysis: [dict]`)
    overwrite structured payloads produced by earlier skills (e.g.
    `analysis: dict`). Preserve object-typed values for known analytical keys
    so multi-skill data chains stay intact.
    """
    merged: dict[str, Any] = {**current}
    for key, value in output.items():
        if key in {"analysis", "rows", "candidates", "findings"} and isinstance(value, list):
            structured = [item for item in value if isinstance(item, dict)]
            if key in merged and isinstance(merged[key], (dict, list)) and merged[key]:
                continue  # keep earlier structured payload
            if structured:
                merged[key] = structured[-1]
                continue
        merged[key] = value
    merged["material"] = output.get("sources", default_material)
    return merged


def skill_execute(ctx: RunContext) -> dict[str, Any]:
    agent = ctx.payload.get("agent")
    chain: list[str] = ctx.payload.get("skill_chain") or []
    executor = SkillExecutor()
    skill_context = SkillContext(
        task_id=ctx.task.id,
        agent_id=getattr(agent, "id", None),
        agent_name=getattr(agent, "name", None),
        workspace=ctx.task.workspace,
        model=getattr(agent, "model", "mock-reasoner"),
    )

    knowledge = KnowledgeService(ctx.db).search(
        ctx.task.title or ctx.task.goal, limit=3, workspace=ctx.task.workspace
    )
    material = [entry.title for entry in knowledge]

    outputs: dict[str, dict[str, Any]] = {}
    current_inputs: dict[str, Any] = {
        "query": ctx.task.goal or ctx.task.title,
        "topic": ctx.task.title,
        "subject": ctx.task.title,
        "material": material,
        **{k: v for k, v in (ctx.task.input_payload or {}).items()},
    }

    for skill_name in chain:
        output, duration_ms = executor.execute(skill_name, current_inputs, context=skill_context)
        outputs[skill_name] = output
        record_event(
            ctx.db,
            "skill.executed",
            service="skill",
            message=skill_name,
            context={"task_id": ctx.task.id, "skill": skill_name, "duration_ms": duration_ms},
        )
        current_inputs = _merge_step_output(current_inputs, output, material)

    ctx.payload["skill_outputs"] = outputs
    ctx.payload["knowledge_refs"] = [entry.id for entry in knowledge]
    return {
        "skills": chain,
        "knowledge_refs": ctx.payload["knowledge_refs"],
        "source_count": len(outputs.get("search", {}).get("sources", [])),
    }


def result_generate(ctx: RunContext) -> dict[str, Any]:
    outputs: dict[str, dict[str, Any]] = ctx.payload.get("skill_outputs") or {}
    report = outputs.get("report") or {}
    content = report.get("content")

    if not content:
        findings = (outputs.get("analysis") or {}).get("findings", [])
        draft = (outputs.get("content") or {}).get("draft", "")
        lines = [f"# {ctx.task.title}", ""]
        if draft:
            lines += [draft, ""]
        lines += [f"- {item}" for item in findings] or ["- 任务已完成，暂无更多结论。"]
        content = "\n".join(lines)

    ctx.task.result = content
    ctx.db.flush()
    record_event(
        ctx.db,
        "result.generated",
        service="agent",
        message=f"{len(content)} chars",
        context={"task_id": ctx.task.id},
    )
    return {"length": len(content), "format": "markdown"}


def save_record(ctx: RunContext) -> dict[str, Any]:
    task = ctx.task
    run = ctx.run
    started = run.started_at
    finished = datetime.now(UTC)
    if started is not None and started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    duration_ms = int((finished - started).total_seconds() * 1000) if started else 0

    task.status = "succeeded"
    task.completed_at = finished
    task.duration_ms = duration_ms
    task.error = None

    run.status = "succeeded"
    run.finished_at = finished
    ctx.db.flush()

    record_event(
        ctx.db,
        "task.completed",
        service="workflow",
        message=task.title,
        context={"task_id": task.id, "duration_ms": duration_ms, "workflow_run": run.id},
    )
    return {"task_status": task.status, "duration_ms": duration_ms}


STEP_HANDLERS = {
    "task_receive": task_receive,
    "agent_select": agent_select,
    "skill_execute": skill_execute,
    "result_generate": result_generate,
    "save_record": save_record,
}
