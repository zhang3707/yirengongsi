"""Convenience entry point used by the API and scripts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from shared.models import Task
from workflow_engine.engine import WorkflowEngine, WorkflowResult


def run_task(db: Session, task: Task, workflow: str = "default") -> WorkflowResult:
    return WorkflowEngine(db).run(task, workflow)
