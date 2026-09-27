"""API Gateway application entry point.

Boot order per the runbook: DB -> Redis -> Temporal(external) -> Backend API ->
Knowledge Service -> Agent Runtime -> Workflow Worker (in-process) -> Console.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from shared.config import PROJECT_ROOT, settings
from shared.database import SessionLocal, init_db
from shared.logging import get_logger

logger = get_logger("backend")
CONSOLE_DIR = PROJECT_ROOT / "console"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from skill_runtime.bootstrap import load_builtin_skills, sync_skills_to_db

    load_builtin_skills()
    logger.info("skill runtime loaded: %s", ", ".join(load_builtin_skills()))

    if settings.auto_create_tables:
        init_db()
        logger.info("database tables ready")

    with SessionLocal() as db:
        sync_skills_to_db(db)
        db.commit()
        if settings.seed_demo_data:
            from backend.seed import seed_demo_data

            seed_demo_data(db)

    logger.info("api gateway started (environment=%s)", settings.environment)
    yield
    logger.info("api gateway stopped")


app = FastAPI(
    title="AI Company MVP v1.0",
    description="AI 员工工作平台 — Pilot 运行环境（Agent / Skill / Workflow / Knowledge）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/console/")


if CONSOLE_DIR.exists():
    app.mount("/console", StaticFiles(directory=str(CONSOLE_DIR), html=True), name="console")
