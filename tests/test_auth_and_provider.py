"""Auth + model provider behaviour."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # ensure project root importable

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from shared.config import settings  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_routes_open_with_auth_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "api_auth_token", "")
    monkeypatch.setattr(settings, "api_auth_enabled", False)
    assert client.get("/api/v1/agents").status_code == 200


def test_routes_protected_with_token(client, monkeypatch):
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_auth_token", "secret-token")

    assert client.get("/api/v1/agents").status_code == 401
    ok = client.get("/api/v1/agents", headers={"Authorization": "Bearer secret-token"})
    assert ok.status_code == 200
    alt = client.get("/api/v1/agents", headers={"X-API-Token": "secret-token"})
    assert alt.status_code == 200
    wrong = client.get("/api/v1/agents", headers={"Authorization": "Bearer wrong"})
    assert wrong.status_code == 401


def test_health_and_console_stay_public_with_auth_on(client, monkeypatch):
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_auth_token", "secret-token")
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/console/").status_code == 200


def test_workflows_listing_requires_token(client, monkeypatch):
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_auth_token", "secret-token")
    assert client.get("/api/v1/workflows").status_code == 401


def test_mock_provider_contents(client, monkeypatch):
    from shared.model_provider import get_model_provider
    from skill_runtime.base import SkillContext
    from skill_runtime.executor import SkillExecutor

    monkeypatch.setattr(settings, "model_provider", "mock")
    provider = get_model_provider()
    assert provider.provider == "mock"

    output, _ = SkillExecutor().execute(
        "search", {"query": "AI 公司 Pilot", "limit": 3}, context=SkillContext()
    )
    assert output["source_count"] == 3
    assert all("fallback_reason" not in s for s in output["sources"])


def test_unknown_provider_falls_back_to_mock(monkeypatch):
    from shared.model_provider import get_model_provider

    monkeypatch.setattr(settings, "model_provider", "never_heard_of_it")
    provider = get_model_provider()
    assert provider.provider == "mock"
