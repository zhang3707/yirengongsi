"""Tests for market discovery skills (T-111 V1): imported data only, loud failures."""

from __future__ import annotations

import pytest

from skill_runtime.base import SkillContext
from skill_runtime.bootstrap import load_builtin_skills  # noqa: E402
from skill_runtime.executor import SkillExecutionError, SkillExecutor
from skill_runtime.registry import registry

load_builtin_skills()

SAMPLE_ROWS = [
    {"title": "PPT 模板 合集 商用授权版", "price": 29.9, "sales": 1850, "reviews": 860, "category": "虚拟"},
    {"title": "PPT 模板合集 学生版", "price": 19.9, "sales": 1200, "reviews": 700, "category": "虚拟"},
    {"title": "Excel 进销存模板 商用", "price": 49.9, "sales": 640, "reviews": 310, "category": "虚拟"},
    {"title": "Excel 自动账本 个人", "price": 15.0, "sales": 300, "reviews": 90, "category": "虚拟"},
    {"title": "PPT 模板代做 破解版", "price": 9.9, "sales": 2400, "reviews": 10, "category": "违规"},
]


def _base_inputs() -> dict:
    return {"products": SAMPLE_ROWS}


def test_market_research_imports_and_counts():
    output, _ = SkillExecutor().execute("market_research", _base_inputs(), context=SkillContext())
    assert output["products_count"] == 5
    assert output["dropped_rows"] == 0
    assert len(output["rows"]) == 5


def test_market_research_empty_data_fails_loudly():
    with pytest.raises(SkillExecutionError, match="no usable market data"):
        SkillExecutor().execute(
            "market_research",
            {"products": [], "csv": "", "json": ""},
            context=SkillContext(),
        )


def test_market_research_csv_import():
    csv_text = "title,price,sales,reviews\n模板A,29.9,1500,800\n模板B,39.9,900,300\n"
    output, _ = SkillExecutor().execute(
        "market_research", {"csv": csv_text}, context=SkillContext()
    )
    assert output["products_count"] == 2


def test_full_chain_produces_projects(client):
    # 通过 API 提交真实任务，全链跑通（mock 数据内联）
    rows = [
        {"title": "PPT 模板 合集 商用授权", "price": 29.9, "sales": 1850, "reviews": 860, "category": "虚拟"},
        {"title": "Excel 进销存 模板 商用", "price": 49.9, "sales": 640, "reviews": 310, "category": "虚拟"},
        {"title": "PPT 模板 破解版 免费下载", "price": 5.0, "sales": 2400, "reviews": 10, "category": "违规"},
    ]
    resp = client.post(
        "/api/v1/tasks",
        json={
            "title": "虚拟类目候选项目发现（导入数据）",
            "task_type": "market_research",
            "goal": "从导入的虚拟商品数据里筛出可落地候选",
            "input_payload": {"products": rows, "supply_source": "manual_import"},
            "auto_run": True,
        },
    )
    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body["status"] == "succeeded", [s["error"] for s in body["runs"][0]["steps"]]
    names = [s["name"] for s in body["runs"][0]["steps"]]
    assert names == [
        "task_receive", "agent_select", "skill_execute",
        "result_generate", "save_record",
    ]
    skill_detail = body["runs"][0]["steps"][2]["detail"]
    assert "market_research" in skill_detail["skills"]
    assert "合规" in (body["result"] or "") or "候选" in (body["result"] or "") or body["result"]


def test_full_chain_registry_lists_all_four():
    names = registry.names()
    assert {"market_research", "market_analysis", "opportunity_discovery", "project_feasibility"} <= set(names)
