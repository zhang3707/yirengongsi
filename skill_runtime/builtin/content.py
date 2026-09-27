"""Content skill: drafts plans / articles / summaries from given material."""

from __future__ import annotations

import json
from typing import Any

from shared.model_provider import ModelProviderError, get_model_provider
from skill_runtime.base import SkillContext, SkillDefinition


def _mock_content(topic: str, material_count: int, content_type: str) -> dict[str, Any]:
    outline = [
        f"背景：{topic} 的当前状况与目标",
        f"要点：基于 {material_count} 条素材提炼关键信息",
        "建议：给出可执行的三步行动方案",
    ]
    drafts = {
        "summary": f"{topic} 摘要：围绕目标整理关键信息，形成可快速阅读的结论。",
        "plan": f"{topic} 方案：分目标、路径、资源与验收四部分推进。",
        "article": f"{topic} 文章：从背景切入，给出论据与行动建议。",
    }
    return {
        "topic": topic,
        "content_type": content_type,
        "outline": outline,
        "draft": drafts.get(content_type, drafts["summary"]),
        "word_hint": 300 + material_count * 50,
    }


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    topic = str(inputs.get("topic") or inputs.get("title") or "内容主题")
    material = inputs.get("material") or []
    content_type = str(inputs.get("content_type") or "summary")
    material_count = len(material) if isinstance(material, list) else 1
    provider = get_model_provider()

    if provider.provider == "mock":
        result = _mock_content(topic, material_count, content_type)
    else:
        system = (
            "你是内容策划。仅输出 JSON (无其他文字)："
            '{"topic": str, "content_type": str, "outline": [str], "draft": str}。'
            "draft 是针对该主题的完整草稿（200-500 字），outline 3-6 条。"
        )
        user = (
            f"主题：{topic}\n类型：{content_type}\n"
            f"素材：{json.dumps(material[:20], ensure_ascii=False)}"
        )
        try:
            reply = provider.complete(system, user, context)
            data = json.loads(reply) if reply.strip().startswith("{") else {}
            if not isinstance(data, dict):
                data = {}
            draft = str(data.get("draft", "")).strip()
            outline = [str(x) for x in (data.get("outline") or []) if str(x).strip()]
            if not draft:
                raise ValueError("empty draft from model")
            result = {
                "topic": str(data.get("topic", topic))[:200],
                "content_type": content_type,
                "outline": outline[:8] or _mock_content(topic, material_count, content_type)["outline"],
                "draft": draft,
                "word_hint": len(draft),
            }
        except (json.JSONDecodeError, ValueError, TypeError, ModelProviderError) as exc:
            result = _mock_content(topic, material_count, content_type)
            result["fallback_reason"] = str(exc)[:120]

    return result


content_skill = SkillDefinition(
    name="content",
    category="content",
    description="根据素材生成摘要、方案或文章草稿，输出结构大纲。",
    handler=_handler,
    input_schema={"topic": "string", "material": "array?", "content_type": "string?"},
    output_schema={"outline": "array", "draft": "string"},
)
