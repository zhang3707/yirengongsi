"""In-process skill registry, mirrored into the `skills` database table."""

from __future__ import annotations

from skill_runtime.base import SkillDefinition, SkillHandler


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, definition: SkillDefinition, *, override: bool = False) -> SkillDefinition:
        if definition.name in self._skills and not override:
            raise ValueError(f"skill already registered: {definition.name}")
        self._skills[definition.name] = definition
        return definition

    def add(
        self,
        name: str,
        *,
        category: str = "general",
        description: str = "",
        handler: SkillHandler,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        override: bool = False,
    ) -> SkillDefinition:
        return self.register(
            SkillDefinition(
                name=name,
                category=category,
                description=description,
                handler=handler,
                input_schema=input_schema or {},
                output_schema=output_schema or {},
            ),
            override=override,
        )

    def get(self, name: str) -> SkillDefinition:
        try:
            return self._skills[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"unknown skill: {name}") from exc

    def has(self, name: str) -> bool:
        return name in self._skills

    def all(self) -> list[SkillDefinition]:
        return sorted(self._skills.values(), key=lambda item: item.name)

    def names(self) -> list[str]:
        return [item.name for item in self.all()]


registry = SkillRegistry()
