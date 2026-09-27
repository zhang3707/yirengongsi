"""ORM models covering the tables required by the runbook:
users, agents, skills, tasks, workflow_runs, knowledge, logs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(40), default="member")
    workspace: Mapped[str] = mapped_column(String(80), default="default")
    status: Mapped[str] = mapped_column(String(20), default="active")

    tasks: Mapped[list[Task]] = relationship(back_populates="user")


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("agt"))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    role: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(60), default="general")
    skills: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    model: Mapped[str] = mapped_column(String(80), default="mock-reasoner")
    memory_enabled: Mapped[bool] = mapped_column(default=True)
    workflow: Mapped[str] = mapped_column(String(80), default="default")
    status: Mapped[str] = mapped_column(String(20), default="active")
    system_prompt: Mapped[str] = mapped_column(Text, default="")


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("skl"))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(60), default="general")
    description: Mapped[str] = mapped_column(Text, default="")
    input_schema: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    output_schema: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    handler: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("task"))
    title: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str] = mapped_column(Text, default="")
    task_type: Mapped[str] = mapped_column(String(40), default="general")
    input_payload: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    expected_output: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="P2")
    assigned_agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    workspace: Mapped[str] = mapped_column(String(80), default="default")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="tasks")
    runs: Mapped[list[WorkflowRun]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wfr"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    workflow: Mapped[str] = mapped_column(String(80), default="default")
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    current_step: Mapped[str] = mapped_column(String(60), default="")
    steps: Mapped[list[dict[str, Any]]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[Task] = relationship(back_populates="runs")


class Knowledge(TimestampMixin, Base):
    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("knw"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source: Mapped[str] = mapped_column(String(200), default="manual")
    workspace: Mapped[str] = mapped_column(String(80), default="default")
    score: Mapped[float] = mapped_column(Float, default=0.0)


class LogEntry(Base):
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("log"))
    level: Mapped[str] = mapped_column(String(10), default="INFO")
    service: Mapped[str] = mapped_column(String(40), default="system")
    event: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class TaskEvaluation(Base):
    """Pilot user scoring for a finished task."""

    __tablename__ = "task_evaluations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("evl"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    quality: Mapped[int] = mapped_column(Integer, default=3)
    minutes_before: Mapped[int] = mapped_column(Integer, default=0)
    minutes_after: Mapped[int] = mapped_column(Integer, default=0)
    time_saved_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    experience: Mapped[int] = mapped_column(Integer, default=3)
    trust: Mapped[int] = mapped_column(Integer, default=3)
    reusable: Mapped[bool] = mapped_column(default=False)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Feedback(Base):
    """Pilot Feedback Pool entry: bug / usability / ai_quality / workflow / feature_request / business_value."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fbk"))
    category: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(String(200))
    scenario: Mapped[str] = mapped_column(Text, default="")
    impact: Mapped[str] = mapped_column(String(20), default="medium")
    frequency: Mapped[str] = mapped_column(String(20), default="medium")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    reporter: Mapped[str] = mapped_column(String(120), default="")
    priority: Mapped[str] = mapped_column(String(10), default="P2")
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

