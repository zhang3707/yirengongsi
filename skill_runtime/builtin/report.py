"""Report skill: assembles findings into a deliverable Markdown report."""

from __future__ import annotations

import json
from typing import Any

from shared.model_provider import ModelProviderError, get_model_provider
from skill_runtime.base import SkillContext, SkillDefinition


def _mock_report(title: str, findings: list, risks: list, sources: list) -> str:
    # T-113c: 检测是否包含 Mock 数据
    has_mock = any(isinstance(s, dict) and s.get('origin') == 'mock' for s in sources)
    
    lines = [f"# {title}", ""]
    
    if has_mock:
        lines += ["⚠️ **本报告包含模拟数据（真实数据源全部失败）**", ""]
    
    lines += ["## 一、核心发现"]
    lines += [f"{index + 1}. {item}" for index, item in enumerate(findings)] or ["1. 暂无可用发现。"]
    lines += ["", "## 二、风险与限制"]
    lines += [f"- {item}" for item in risks] or ["- 暂无记录。"]
    lines += ["", "## 三、资料线索"]
    for source in sources:
        if isinstance(source, dict):
            url_part = f" [{source.get('url')}]" if source.get('url') else ""
            lines.append(f"- {source.get('title', '未命名')}（来源：{source.get('origin', 'unknown')}）{url_part}")
    lines += ["", "## 四、人工复核建议", "- 由业务负责人复核结论后交付。"]
    return "\n".join(lines)


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    title = str(inputs.get("title") or inputs.get("subject") or "任务分析报告")
    findings = inputs.get("findings") or []
    risks = inputs.get("risks") or []
    sources = inputs.get("sources") or []
    provider = get_model_provider()

    if provider.provider == "mock":
        content = _mock_report(title, findings, risks, sources)
    else:
        system = (
            "你是报告撰写人。输出结构化中文 Markdown 报告（不输出 JSON），包含 "
            "# 标题 / ## 一、核心发现 / ## 二、风险与限制 / ## 三、资料线索 / ## 四、人工复核建议。"
            "内容必须围绕 findings 与 sources 展开，不要复述模板句。"
        )
        user = (
            f"报告标题：{title}\n"
            f"核心发现：{json.dumps(findings, ensure_ascii=False)}\n"
            f"风险：{json.dumps(risks, ensure_ascii=False)}\n"
            f"资料：{json.dumps(sources[:20], ensure_ascii=False)}"
        )
        try:
            content = provider.complete(system, user, context).strip()
            if len(content) < 60:
                raise ValueError("model report too short")
        except (ValueError, ModelProviderError) as exc:
            content = _mock_report(title, findings, risks, sources)
            content += f"\n\n> fallback_reason: {str(exc)[:120]}"

    return {
        "title": title,
        "format": "markdown",
        "content": content,
        "section_count": 4,
        "generator": context.agent_name or "Report Agent",
    }


report_skill = SkillDefinition(
    name="report",
    category="content",
    description="把分析结论组织成可交付的 Markdown 报告。",
    handler=_handler,
    input_schema={"title": "string", "findings": "array", "risks": "array?"},
    output_schema={"format": "string", "content": "string"},
)
