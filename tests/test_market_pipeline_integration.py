"""Integration test for T-112: market_research → analysis → opportunity → feasibility → report 链路"""

import pytest

from skill_runtime.builtin.market_discovery import (
    _market_analysis,
    _market_research,
    _opportunity_discovery,
    _project_feasibility,
)
from skill_runtime.builtin.report import _handler as report_handler


class MockContext:
    """测试用 SkillContext"""
    def __init__(self, agent_name="Test Agent"):
        self.agent_name = agent_name
        self.task_id = "test-task"
        self.agent_id = "test-agent"
        self.workspace = "test"
        self.model = "mock-reasoner"



def test_full_pipeline_produces_findings_and_sources():
    """完整链路：手动导入数据 → 分析 → 机会发现 → 可行性评估 → 报告生成"""
    
    # 1. market_research: 手动导入数据
    research_inputs = {
        "products": [
            {"title": "PPT模板-商务风", "price": 19.9, "sales": 1832, "reviews": 860, "category": "PPT模板", "url": "https://item.taobao.com/1", "platform": "taobao"},
            {"title": "PPT模板-简约风", "price": 29.9, "sales": 2100, "reviews": 1200, "category": "PPT模板", "url": "https://item.taobao.com/2", "platform": "taobao"},
            {"title": "PPT模板-教育风", "price": 15.9, "sales": 980, "reviews": 450, "category": "PPT模板", "url": "https://item.taobao.com/3", "platform": "taobao"},
        ]
    }
    research_output = _market_research(MockContext(), research_inputs)
    assert research_output["products_count"] == 3
    assert len(research_output["rows"]) == 3
    
    # 2. market_analysis: 分析指标
    analysis_inputs = {"rows": research_output["rows"]}
    analysis_output = _market_analysis(MockContext(), analysis_inputs)
    assert analysis_output["rows_count"] == 3
    assert "demand_score" in analysis_output
    assert "competition_score" in analysis_output
    
    # 3. opportunity_discovery: 筛选候选
    opportunity_inputs = {"rows": research_output["rows"], "analysis": analysis_output}
    opportunity_output = _opportunity_discovery(MockContext(), opportunity_inputs)
    assert len(opportunity_output["candidates"]) > 0
    
    # 4. project_feasibility: 生成项目卡片 + findings/risks/sources
    feasibility_inputs = {"candidates": opportunity_output["candidates"]}
    feasibility_output = _project_feasibility(MockContext(), feasibility_inputs)
    
    # 验证：projects 字段存在
    assert "projects" in feasibility_output
    assert len(feasibility_output["projects"]) > 0
    
    # 验证：findings 字段存在且不为空（T-112 修复）
    assert "findings" in feasibility_output
    assert len(feasibility_output["findings"]) > 0
    
    # 验证：risks 字段存在
    assert "risks" in feasibility_output
    assert len(feasibility_output["risks"]) > 0
    
    # 验证：sources 字段存在且包含 URL（T-112 修复）
    assert "sources" in feasibility_output
    assert len(feasibility_output["sources"]) > 0
    assert all("url" in src for src in feasibility_output["sources"])
    
    # 5. report: 生成报告
    report_inputs = {
        "title": "PPT模板市场分析",
        "findings": feasibility_output["findings"],
        "risks": feasibility_output["risks"],
        "sources": feasibility_output["sources"],
    }
    report_output = report_handler(MockContext(), report_inputs)
    
    # 验证：报告内容包含真实数据（不是"暂无可用发现"）
    assert "content" in report_output
    content = report_output["content"]
    assert "PPT模板" in content
    assert "暂无可用发现" not in content  # T-112 修复的关键验证
    
    # 验证：报告包含 sources（资料线索）
    assert "资料线索" in content
    assert "https://item.taobao.com" in content


def test_pipeline_with_empty_projects_still_generates_findings():
    """边界情况：即使 projects 为空，也应该生成默认 findings"""
    
    # 直接调用 project_feasibility，传入空 candidates
    feasibility_inputs = {"candidates": []}
    
    with pytest.raises(ValueError, match="no candidates to assess"):
        _project_feasibility(MockContext(), feasibility_inputs)


def test_pipeline_findings_fallback_to_titles():
    """如果 projects 没有 problem 字段，findings 应该回退到标题"""
    
    # 构造一个没有 problem 字段的 candidates
    candidates = [
        {"title": "PPT模板-商务风", "price": 19.9, "sales": 1832, "url": "https://item.taobao.com/1", "platform": "taobao"},
    ]
    
    feasibility_inputs = {"candidates": candidates}
    feasibility_output = _project_feasibility(MockContext(), feasibility_inputs)
    
    # 验证：findings 回退到标题
    assert len(feasibility_output["findings"]) > 0
    assert "PPT模板-商务风" in feasibility_output["findings"][0]
