"""Task endpoints: submit, run the workflow, read result, evaluate (Pilot feedback)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from backend.api.auth import require_token
from backend.api.deps import DbSession
from shared.events import record_event
from shared.models import Task, TaskEvaluation, User, WorkflowRun
from shared.schemas import (
    TaskCreate,
    TaskDetail,
    TaskEvaluationRead,
    TaskRead,
    WorkflowRunRead,
)
from shared.schemas import (
    TaskEvaluation as TaskEvaluationIn,
)
from workflow_engine.runner import run_task

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_token)])


def _resolve_user(db, email: str | None) -> User | None:
    if not email:
        return None
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=email.split("@")[0], email=email, role="member")
        db.add(user)
        db.flush()
    return user


@router.get("", response_model=list[TaskRead])
def list_tasks(db: DbSession, status: str | None = None, limit: int = 50) -> list[TaskRead]:
    stmt = select(Task).order_by(Task.created_at.desc()).limit(min(limit, 200))
    if status:
        stmt = stmt.where(Task.status == status)
    return [TaskRead.model_validate(row) for row in db.scalars(stmt)]


@router.post("", response_model=TaskDetail, status_code=201)
def create_task(payload: TaskCreate, db: DbSession) -> TaskDetail:
    user = _resolve_user(db, payload.user_email)
    task = Task(
        title=payload.title,
        goal=payload.goal or payload.title,
        task_type=payload.task_type,
        input_payload=payload.input_payload,
        expected_output=payload.expected_output,
        acceptance_criteria=payload.acceptance_criteria,
        priority=payload.priority,
        workspace=payload.workspace,
        user_id=user.id if user else None,
        status="pending",
    )
    db.add(task)
    db.flush()
    record_event(
        db,
        "task.created",
        service="backend",
        message=task.title,
        context={"task_id": task.id, "task_type": task.task_type, "priority": task.priority},
    )
    db.commit()

    if payload.auto_run:
        run_task(db, task)
        db.refresh(task)
    return _detail(db, task)


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, db: DbSession) -> TaskDetail:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _detail(db, task)


@router.post("/{task_id}/run", response_model=TaskDetail)
def run_existing_task(task_id: str, db: DbSession) -> TaskDetail:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status == "running":
        raise HTTPException(status_code=409, detail="task is already running")
    result = run_task(db, task)
    db.refresh(task)
    if not result.ok:
        raise HTTPException(status_code=500, detail=f"workflow failed at {result.failed_step}")
    return _detail(db, task)


@router.post("/{task_id}/evaluation", response_model=TaskEvaluationRead, status_code=201)
def evaluate_task(task_id: str, payload: TaskEvaluationIn, db: DbSession) -> TaskEvaluationRead:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    ratio = 0.0
    if payload.minutes_before > 0:
        saved = max(payload.minutes_before - payload.minutes_after, 0)
        ratio = round(saved / payload.minutes_before, 3)

    evaluation = TaskEvaluation(
        task_id=task_id,
        quality=payload.quality,
        minutes_before=payload.minutes_before,
        minutes_after=payload.minutes_after,
        time_saved_ratio=ratio,
        experience=payload.experience,
        trust=payload.trust,
        reusable=payload.reusable,
        comment=payload.comment,
    )
    db.add(evaluation)
    record_event(
        db,
        "task.evaluated",
        service="backend",
        message=f"quality={payload.quality}",
        context={"task_id": task_id, "time_saved_ratio": ratio},
    )
    db.commit()
    return TaskEvaluationRead.model_validate(evaluation)


def _detail(db, task: Task) -> TaskDetail:
    runs = db.scalars(
        select(WorkflowRun).where(WorkflowRun.task_id == task.id).order_by(WorkflowRun.started_at)
    ).all()
    detail = TaskDetail.model_validate(task)
    detail.runs = [WorkflowRunRead.model_validate(run) for run in runs]
    return detail

