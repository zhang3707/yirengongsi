"""Skill contract: every skill declares input/output schema and a handler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

SkillHandler = Callable[["SkillContext", dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class SkillContext:
    """Runtime context passed to a skill handler."""

    task_id: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    workspace: str = "default"
    model: str = "mock-reasoner"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillDefinition:
    name: str
    category: str
    description: str
    handler: SkillHandler
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    @property
    def handler_name(self) -> str:
        return f"builtin:{self.name}"
