"""Analysis skill: turns collected material into findings, risks and next actions."""

from __future__ import annotations

import json
from typing import Any

from shared.model_provider import ModelProviderError, get_model_provider
from skill_runtime.base import SkillContext, SkillDefinition


def _mock_analysis(subject: str, material_count: int, has_data: bool) -> dict[str, Any]:
    findings = [
        f"{subject} 的关键变化集中在需求侧与执行效率两个方向。",
        f"当前已收集到 {material_count} 条资料线索，可支撑初步结论。",
    ]
    if has_data:
        findings.append("数据输入包含可用于量化校验的字段。")
    risks = [
        "资料来源覆盖度不足时结论置信度下降，需要人工复核。",
        "缺少统一评价标准时，输出质量难以跨任务比较。",
    ]
    return {
        "subject": subject,
        "findings": findings,
        "risks": risks,
        "confidence": 0.72 if material_count else 0.55,
        "analyst": "Analytics Agent",
    }


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    subject = str(inputs.get("subject") or inputs.get("topic") or inputs.get("query") or "任务主题")
    material = inputs.get("material") or inputs.get("sources") or []
    data_points = inputs.get("data") or {}
    material_count = len(material) if isinstance(material, list) else 1
    provider = get_model_provider()

    if provider.provider == "mock":
        result = _mock_analysis(subject, material_count, bool(data_points))
    else:
        system = (
            "你是业务分析师。仅输出 JSON（无其他文字）："
            '{"subject": str, "findings": [str], "risks": [str], "confidence": 0-1 float}。'
            "findings 2-5 条、risks 1-5 条，与分析对象直接相关，不要复述模板句。"
        )
        user = (
            f"分析对象：{subject}\n素材条数：{material_count}\n"
            f"素材列表：{json.dumps(material[:20], ensure_ascii=False)}"
        )
        try:
            reply = provider.complete(system, user, context)
            data = json.loads(reply) if reply.strip().startswith("{") else {}
            if not isinstance(data, dict):
                data = {}
            findings = [str(x) for x in (data.get("findings") or []) if str(x).strip()]
            risks = [str(x) for x in (data.get("risks") or []) if str(x).strip()]
            if not findings:
                raise ValueError("empty findings from model")
            result = {
                "subject": str(data.get("subject", subject))[:200],
                "findings": findings[:8],
                "risks": risks[:8],
                "confidence": min(1.0, max(0.0, float(data.get("confidence", 0.6)))),
                "analyst": context.agent_name or "Analytics Agent",
            }
        except (json.JSONDecodeError, ValueError, TypeError, ModelProviderError) as exc:
            result = _mock_analysis(subject, material_count, bool(data_points))
            result["fallback_reason"] = str(exc)[:120]

    result["analyst"] = context.agent_name or result.get("analyst", "Analytics Agent")
    return result


analysis_skill = SkillDefinition(
    name="analysis",
    category="analysis",
    description="对资料或数据做结构化分析，输出发现、风险与置信度。",
    handler=_handler,
    input_schema={"subject": "string", "material": "array?", "data": "object?"},
    output_schema={"subject": "string", "findings": "array", "risks": "array", "confidence": "float"},
)
