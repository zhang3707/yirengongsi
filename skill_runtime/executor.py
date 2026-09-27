"""Skill executor: resolves the handler, runs it, measures duration and logs failures."""

from __future__ import annotations

import time
from typing import Any

from skill_runtime.base import SkillContext
from skill_runtime.registry import registry


class SkillTimeoutError(TimeoutError):
    pass


class SkillExecutor:
    def __init__(self, skills=None) -> None:
        self.skills = skills or registry

    def execute(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        *,
        context: SkillContext | None = None,
    ) -> tuple[dict[str, Any], int]:
        definition = self.skills.get(name)
        started = time.perf_counter()
        try:
            output = definition.handler(context or SkillContext(), dict(inputs or {}))
        except Exception as exc:
            raise SkillExecutionError(name, str(exc)) from exc
        duration_ms = int((time.perf_counter() - started) * 1000)

        if not isinstance(output, dict):
            raise SkillExecutionError(name, f"handler returned {type(output).__name__}, expected dict")
        output.setdefault("skill", name)
        return output, duration_ms


class SkillExecutionError(RuntimeError):
    def __init__(self, skill: str, reason: str) -> None:
        super().__init__(f"skill '{skill}' failed: {reason}")
        self.skill = skill
        self.reason = reason


def execute_skill(
    name: str,
    inputs: dict[str, Any] | None = None,
    *,
    context: SkillContext | None = None,
) -> tuple[dict[str, Any], int]:
    return SkillExecutor().execute(name, inputs, context=context)
