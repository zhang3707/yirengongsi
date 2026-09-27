"""Tests for the ecommerce_publish skill (pure function mocks; no network, no browser)."""

from __future__ import annotations

from typing import Any

import pytest

from shared.config import settings
from skill_runtime.base import SkillContext
from skill_runtime.bootstrap import load_builtin_skills  # noqa: E402
from skill_runtime.executor import SkillExecutionError, SkillExecutor
from skill_runtime.registry import registry

load_builtin_skills()

import skill_runtime.builtin.ecommerce_publish as mod  # noqa: E402


class _FakeClient:
    """Simple stub recording calls and returning canned publish-service payloads."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True,
                "data": {"request": {"image": "x"},
                         "report": [f"built from {payload.get('productDir')}"]}}

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "code": "SUCCESS"}

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.posts.append(("run", payload))
        if payload.get("dryRun"):
            return {"ok": True, "code": "SUCCESS", "data": {}}
        return {"ok": True, "code": "SUCCESS",
                "data": {"runId": "r-1", "meta": {"via": "daemon"}}}

    def status(self, run_id: str) -> dict[str, Any]:
        return {"ok": True, "code": "SUCCESS",
                "data": {"runId": run_id, "status": "finished", "goodsId": "TB-001"}}


@pytest.fixture()
def stub(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(settings, "ecom_autopilot_base_url", "http://stub.invalid")

    def fake_post(client, path, payload):
        if path == mod._URL_BUILD:
            return fake.build(payload)
        if path == mod._URL_VALIDATE:
            return fake.validate(payload)
        if path == mod._URL_RUN:
            return fake.run(payload)
        raise AssertionError(f"unexpected post {path}")

    def fake_get(client, path):
        if path.startswith(mod._URL_STATUS):
            return fake.status(path.rsplit("/", 1)[-1])
        raise AssertionError(f"unexpected get {path}")

    monkeypatch.setattr(mod, "_post", fake_post)
    monkeypatch.setattr(mod, "_get", fake_get)
    return fake


def _execute(inputs: dict) -> dict:
    output, _ = SkillExecutor().execute("ecommerce_publish", inputs, context=SkillContext())
    return output


def test_ecommerce_publish_registered():
    assert "ecommerce_publish" in registry.names()


def test_publish_requires_product_dir(stub):
    with pytest.raises(SkillExecutionError, match="product_dir is required"):
        _execute({})


def test_publish_requires_base_url(monkeypatch):
    monkeypatch.setattr(settings, "ecom_autopilot_base_url", "")
    with pytest.raises(SkillExecutionError, match="ECOM_AUTOPILOT_BASE_URL"):
        _execute({"product_dir": "products/X"})


def test_publish_real_run_requires_policy_approval(stub):
    inputs = {"product_dir": "products/DJ-2026-001", "dry_run": False}
    with pytest.raises(SkillExecutionError, match="policy_approval"):
        _execute(inputs)


def test_publish_dry_run_reports_report(stub):
    inputs = {"product_dir": "products/DJ-2026-001", "dry_run": True}
    output = _execute(inputs)
    assert output["product_dir"] == "products/DJ-2026-001"
    assert output["dry_run"] is True
    assert output["validation_ok"] is True
    md = output.get("report_markdown") or ""
    assert "电商发布报告" in md
    assert "products/DJ-2026-001" in md


def test_publish_real_run_with_approval(stub):
    inputs = {
        "product_dir": "products/DJ-2026-001",
        "dry_run": False,
        "policy_approval": {"allowed": True, "token": "publish"},
    }
    output = _execute(inputs)
    assert output["dry_run"] is False
    assert output["run"]["goodsId"] == "TB-001"
    assert output["run"]["status"] == "finished"
    assert output["validation_ok"] is True


def test_publish_maps_to_task_chain(client):
    response = client.get("/api/v1/skills/registry")
    assert response.status_code == 200
    assert "ecommerce_publish" in response.json()
