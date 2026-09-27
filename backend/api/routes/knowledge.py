"""Knowledge endpoints backing the Knowledge System."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import require_token
from backend.api.deps import DbSession
from knowledge_service.service import KnowledgeService
from shared.schemas import KnowledgeCreate, KnowledgeRead

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require_token)])


@router.get("", response_model=list[KnowledgeRead])
def list_entries(db: DbSession, workspace: str | None = None, limit: int = 50) -> list[KnowledgeRead]:
    return [
        KnowledgeRead.model_validate(row)
        for row in KnowledgeService(db).list(workspace=workspace, limit=min(limit, 200))
    ]


@router.post("", response_model=KnowledgeRead, status_code=201)
def create_entry(payload: KnowledgeCreate, db: DbSession) -> KnowledgeRead:
    entry = KnowledgeService(db).create(**payload.model_dump())
    db.commit()
    return KnowledgeRead.model_validate(entry)


@router.get("/search", response_model=list[KnowledgeRead])
def search_entries(db: DbSession, q: str, limit: int = 5) -> list[KnowledgeRead]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="query 'q' must not be empty")
    return [
        KnowledgeRead.model_validate(row)
        for row in KnowledgeService(db).search(q, limit=min(limit, 50))
    ]
