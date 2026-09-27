"""Pydantic request/response schemas shared by the API and runtimes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["pending", "running", "succeeded", "failed", "cancelled"]
TaskPriority = Literal["P0", "P1", "P2", "P3"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- Health ----------------

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    database: str
    redis: str
    services: dict[str, str]


# ---------------- Agent ----------------

class AgentCreate(BaseModel):
    name: str
    role: str = ""
    description: str = ""
    domain: str = "general"
    skills: list[str] = Field(default_factory=list)
    model: str = "mock-reasoner"
    memory_enabled: bool = True
    workflow: str = "default"
    system_prompt: str = ""


class AgentRead(ORMModel):
    id: str
    name: str
    role: str
    description: str
    domain: str
    skills: list[str]
    model: str
    memory_enabled: bool
    workflow: str
    status: str
    created_at: datetime


# ---------------- Skill ----------------

class SkillCreate(BaseModel):
    name: str
    category: str = "general"
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    handler: str = ""


class SkillRead(ORMModel):
    id: str
    name: str
    category: str
    description: str
    handler: str
    status: str
    created_at: datetime


class SkillRunRequest(BaseModel):
    skill: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class SkillRunResponse(BaseModel):
    skill: str
    output: dict[str, Any]
    duration_ms: int


# ---------------- Task ----------------

class TaskCreate(BaseModel):
    title: str
    goal: str = ""
    task_type: str = "general"
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: str = ""
    acceptance_criteria: str = ""
    priority: TaskPriority = "P2"
    workspace: str = "default"
    user_email: str | None = None
    auto_run: bool = True


class TaskRead(ORMModel):
    id: str
    title: str
    goal: str
    task_type: str
    status: str
    priority: str
    assigned_agent_id: str | None
    workspace: str
    result: str | None
    error: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None


class TaskDetail(TaskRead):
    runs: list[WorkflowRunRead] = Field(default_factory=list)


class TaskEvaluation(BaseModel):
    """Pilot feedback scoring (quality / time saved / experience / trust)."""

    quality: int = Field(ge=1, le=5)
    minutes_before: int = Field(ge=0, default=0)
    minutes_after: int = Field(ge=0, default=0)
    experience: int = Field(ge=1, le=5)
    trust: int = Field(ge=1, le=5)
    reusable: bool = False
    comment: str = ""


class TaskEvaluationRead(ORMModel):
    id: str
    task_id: str
    quality: int
    minutes_before: int
    minutes_after: int
    time_saved_ratio: float
    experience: int
    trust: int
    reusable: bool
    comment: str
    created_at: datetime


# ---------------- Workflow ----------------

class WorkflowStepRead(BaseModel):
    name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class WorkflowRunRead(ORMModel):
    id: str
    task_id: str
    workflow: str
    status: str
    current_step: str
    steps: list[dict[str, Any]]
    retries: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class WorkflowRead(BaseModel):
    name: str
    description: str
    steps: list[str]


# ---------------- Knowledge ----------------

class KnowledgeCreate(BaseModel):
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    workspace: str = "default"


class KnowledgeRead(ORMModel):
    id: str
    title: str
    content: str
    tags: list[str]
    source: str
    workspace: str
    created_at: datetime


# ---------------- Feedback / Issue pool ----------------

class FeedbackCreate(BaseModel):
    category: Literal[
        "bug", "usability", "ai_quality", "workflow", "feature_request", "business_value"
    ]
    summary: str
    scenario: str = ""
    impact: str = ""
    frequency: str = ""
    suggestion: str = ""
    task_id: str | None = None
    reporter: str = ""


class FeedbackRead(ORMModel):
    id: str
    category: str
    summary: str
    scenario: str
    impact: str
    frequency: str
    suggestion: str
    task_id: str | None
    reporter: str
    priority: str
    status: str
    created_at: datetime


TaskDetail.model_rebuild()
