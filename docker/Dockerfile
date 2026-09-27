# AI Company MVP v1.0 — API Gateway + Agent/Skill/Workflow runtimes (single Pilot image)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY shared ./shared
COPY backend ./backend
COPY agent_runtime ./agent_runtime
COPY skill_runtime ./skill_runtime
COPY workflow_engine ./workflow_engine
COPY knowledge_service ./knowledge_service
COPY console ./console
COPY database ./database

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
