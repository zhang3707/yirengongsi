"""Test fixtures: isolated SQLite database per test session + FastAPI TestClient.

The DATABASE_URL is overridden *before* `shared.config` is imported anywhere else,
so the app never touches the developer's local data/ database.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_TMP_DIR = tempfile.mkdtemp(prefix="ai_company_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["LOG_DIR"] = str(Path(_TMP_DIR, "logs"))
os.environ["STORAGE_PATH"] = str(Path(_TMP_DIR, "storage"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    from shared.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
