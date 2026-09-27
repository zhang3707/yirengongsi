"""Register built-in skills into the in-process registry and sync them to the DB."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models import Skill
from skill_runtime.builtin import BUILTIN_SKILLS
from skill_runtime.registry import registry

logger = get_logger("skill")


def load_builtin_skills(*, override: bool = True) -> list[str]:
    for definition in BUILTIN_SKILLS:
        registry.register(definition, override=override)
    return registry.names()


def sync_skills_to_db(db: Session) -> int:
    """Upsert registered skills into the `skills` table."""
    count = 0
    for definition in registry.all():
        row = db.scalar(select(Skill).where(Skill.name == definition.name))
        if row is None:
            row = Skill(name=definition.name)
            db.add(row)
        row.category = definition.category
        row.description = definition.description
        row.input_schema = definition.input_schema
        row.output_schema = definition.output_schema
        row.handler = definition.handler_name
        row.status = "active"
        count += 1
    db.flush()
    logger.info("synced %s skills to database", count)
    return count
