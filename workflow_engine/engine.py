"""Workflow engine: executes a workflow definition for a task, persisting each step.

Persistence contract (from the runbook):
  * every step is written to `workflow_runs.steps` as it starts and finishes
  * failures mark the task failed, keep the error, and are logged to `logs`
  * the retry step (skill_execute by default) is retried up to MAX_WORKFLOW_RETRIES
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from shared.config import settings
from shared.events import record_event
from shared.logging import get_logger
from shared.models import Task, WorkflowRun
from workflow_engine.definitions import WorkflowDefinition, get_workflow
from workflow_engine.state import mark_failed, mark_running, mark_succeeded, new_step
from workflow_engine.steps import STEP_HANDLERS, RunContext

logger = get_logger("workflow")


@dataclass(slots=True)
class WorkflowResult:
    run: WorkflowRun
    task: Task
    ok: bool
    failed_step: str | None = None

    @property
    def report(self) -> str | None:
        return self.task.result


class WorkflowEngine:
    def __init__(self, db: Session, *, max_retries: int | None = None) -> None:
        self.db = db
        self.max_retries = settings.max_workflow_retries if max_retries is None else max_retries

    def _sync_steps(self, run: WorkflowRun) -> None:
        """JSON columns compare by value; nested dict edits need an explicit dirty flag."""
        flag_modified(run, "steps")

    def run(self, task: Task, workflow: str | WorkflowDefinition = "default") -> WorkflowResult:
        definition = workflow if isinstance(workflow, WorkflowDefinition) else get_workflow(workflow)

        run = WorkflowRun(
            task_id=task.id,
            workflow=definition.name,
            status="running",
            current_step=definition.steps[0],
            steps=[new_step(name) for name in definition.steps],
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.flush()

        context = RunContext(db=self.db, task=task, run=run)
        logger.info("workflow %s started for task %s", definition.name, task.id)
        record_event(
            self.db,
            "workflow.started",
            service="workflow",
            message=definition.name,
            context={"task_id": task.id, "run_id": run.id, "steps": definition.steps},
        )
        self.db.commit()

        for index, step_name in enumerate(definition.steps):
            step = run.steps[index]
            mark_running(step)
            run.current_step = step_name
            self._sync_steps(run)
            self.db.commit()

            handler = STEP_HANDLERS[step_name]
            attempts = 0
            while True:
                try:
                    detail = handler(context) or {}
                    mark_succeeded(step, detail)
                    self._sync_steps(run)
                    self.db.commit()
                    break
                except Exception as exc:  # noqa: BLE001 - recorded, then retried or failed
                    attempts += 1
                    # Risk-governance codes must NOT be retried (avoid retry storm).
                    code = getattr(exc, "code", None) or ""
                    if code in {"ANTIBOT_BLOCKED", "LOGIN_REQUIRED", "EMPTY_PAGE", "COMMAND_TIMEOUT"}:
                        can_retry = False
                    else:
                        can_retry = step_name == definition.retry_step and attempts <= self.max_retries
                    record_event(
                        self.db,
                        "workflow.step_failed",
                        service="workflow",
                        level="ERROR",
                        message=f"{step_name}: {exc}",
                        context={
                            "task_id": task.id,
                            "run_id": run.id,
                            "step": step_name,
                            "attempt": attempts,
                            "will_retry": can_retry,
                        },
                    )
                    if can_retry:
                        run.retries += 1
                        self.db.commit()
                        logger.warning("retrying step %s (attempt %s)", step_name, attempts + 1)
                        continue

                    mark_failed(step, str(exc))
                    run.status = "failed"
                    run.error = str(exc)
                    run.finished_at = datetime.now(UTC)
                    task.status = "failed"
                    task.error = str(exc)
                    task.completed_at = run.finished_at
                    self._sync_steps(run)
                    self.db.commit()
                    logger.error("workflow failed at %s: %s", step_name, exc)
                    return WorkflowResult(run=run, task=task, ok=False, failed_step=step_name)

        run.status = "succeeded"
        run.current_step = "done"
        run.finished_at = run.finished_at or datetime.now(UTC)
        self.db.commit()
        logger.info("workflow %s finished for task %s", definition.name, task.id)
        return WorkflowResult(run=run, task=task, ok=True)


