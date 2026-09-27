"""Workflow endpoints: list definitions, inspect and rerun workflow runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from backend.api.auth import require_token
from backend.api.deps import DbSession
from shared.models import Task, WorkflowRun
from shared.schemas import WorkflowRead, WorkflowRunRead
from workflow_engine.definitions import list_workflows
from workflow_engine.runner import run_task

router = APIRouter(prefix="/workflows", tags=["workflows"], dependencies=[Depends(require_token)])


@router.get("", response_model=list[WorkflowRead])
def list_definitions() -> list[WorkflowRead]:
    return [
        WorkflowRead(name=item.name, description=item.description, steps=list(item.steps))
        for item in list_workflows()
    ]


@router.get("/runs", response_model=list[WorkflowRunRead])
def list_runs(db: DbSession, status: str | None = None, limit: int = 50) -> list[WorkflowRunRead]:
    stmt = select(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(min(limit, 200))
    if status:
        stmt = stmt.where(WorkflowRun.status == status)
    return [WorkflowRunRead.model_validate(row) for row in db.scalars(stmt)]


@router.get("/runs/{run_id}", response_model=WorkflowRunRead)
def get_run(run_id: str, db: DbSession) -> WorkflowRunRead:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow run not found")
    return WorkflowRunRead.model_validate(run)


@router.post("/runs/{run_id}/retry", response_model=WorkflowRunRead)
def retry_run(run_id: str, db: DbSession) -> WorkflowRunRead:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow run not found")
    task = db.get(Task, run.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    result = run_task(db, task, run.workflow)
    if not result.ok:
        raise HTTPException(status_code=500, detail=f"workflow failed at {result.failed_step}")
    return WorkflowRunRead.model_validate(result.run)
