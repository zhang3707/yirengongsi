"""initial schema: users/agents/skills/tasks/workflow_runs/knowledge/logs/feedback

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    "task_evaluations",
    "feedback",
    "logs",
    "workflow_runs",
    "tasks",
    "knowledge",
    "skills",
    "agents",
    "users",
]


def upgrade() -> None:
    """Create the Pilot schema directly from ORM metadata (single source of truth)."""
    import shared.models  # noqa: F401
    from shared.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import shared.models  # noqa: F401
    from shared.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
