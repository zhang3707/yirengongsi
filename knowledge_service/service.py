"""Knowledge service used by research/content skills and the Console."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models import Knowledge

logger = get_logger("system")


class KnowledgeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        title: str,
        content: str,
        tags: list[str] | None = None,
        source: str = "manual",
        workspace: str = "default",
    ) -> Knowledge:
        entry = Knowledge(
            title=title,
            content=content,
            tags=tags or [],
            source=source,
            workspace=workspace,
        )
        self.db.add(entry)
        self.db.flush()
        logger.info("knowledge stored: %s", entry.id)
        return entry

    def get(self, knowledge_id: str) -> Knowledge | None:
        return self.db.get(Knowledge, knowledge_id)

    def list(self, *, workspace: str | None = None, limit: int = 50) -> list[Knowledge]:
        stmt = select(Knowledge)
        if workspace:
            stmt = stmt.where(Knowledge.workspace == workspace)
        stmt = stmt.order_by(Knowledge.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def search(self, query: str, *, limit: int = 5, workspace: str | None = None) -> list[Knowledge]:
        """Keyword search across title/content/tags with a simple relevance score."""
        terms = [term for term in query.replace("，", " ").replace(",", " ").split() if term]
        stmt = select(Knowledge)
        if workspace:
            stmt = stmt.where(Knowledge.workspace == workspace)
        if terms:
            conditions = []
            for term in terms:
                pattern = f"%{term}%"
                conditions.append(
                    or_(
                        Knowledge.title.ilike(pattern),
                        Knowledge.content.ilike(pattern),
                    )
                )
            stmt = stmt.where(or_(*conditions))
        rows = list(self.db.scalars(stmt.limit(max(limit * 5, limit))))

        def score(entry: Knowledge) -> float:
            text = f"{entry.title} {entry.content} {' '.join(entry.tags or [])}"
            hits = sum(1 for term in terms if term and term in text)
            return float(hits)

        rows.sort(key=lambda entry: (-score(entry), entry.title))
        results = rows[:limit]
        for entry in results:
            entry.score = score(entry)
        self.db.flush()
        return results


def search_knowledge(db: Session, query: str, *, limit: int = 5) -> list[Knowledge]:
    return KnowledgeService(db).search(query, limit=limit)
