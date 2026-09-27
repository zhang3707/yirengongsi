"""Search skill: collects candidate sources for a research task.

Model mode asks the LLM for candidate sources; mock mode keeps the
deterministic, reviewable source list used by the tests.
"""

from __future__ import annotations

import json
from typing import Any

from shared.model_provider import ModelProviderError, get_model_provider
from skill_runtime.base import SkillContext, SkillDefinition


def _mock_sources(query: str, limit: int) -> list[dict[str, Any]]:
    return [
        {
            "title": f"{query or '任务主题'} — 资料线索 {index + 1}",
            "origin": "knowledge_base" if index == 0 else "web_candidate",
            "relevance": round(max(0.35, 0.95 - index * 0.1), 2),
        }
        for index in range(max(1, min(limit, 10)))
    ]


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    query = str(inputs.get("query") or inputs.get("topic") or "").strip()
    limit = int(inputs.get("limit") or 5)
    provider = get_model_provider()

    if provider.provider == "mock":
        sources = _mock_sources(query, limit)
    else:
        system = (
            "You are a research assistant. Return ONLY a JSON array (no prose) of up to"
            " 5 objects with keys: title, origin, relevance (0-1 float)."
            " Base candidates on general knowledge; do not fabricate URLs."
        )
        user = f"Research query: {query}\nReturn up to 5 candidate sources."
        try:
            reply = provider.complete(system, user, context)
            data = json.loads(reply) if reply.strip().startswith("[") else []
            if not isinstance(data, list):
                data = []
            sources = [
                {
                    "title": str(item.get("title", "未命名"))[:200],
                    "origin": str(item.get("origin", "web"))[:80],
                    "relevance": float(item.get("relevance", 0.5)),
                }
                for item in data[:5]
            ]
            if not sources:
                raise ValueError("empty source list from model")
        except (json.JSONDecodeError, ValueError, TypeError, ModelProviderError) as exc:
            # 模型失败时回落确定性列表，但在输出里显式标注，不让工作流静默降级。
            sources = _mock_sources(query, limit)
            sources[0]["fallback_reason"] = str(exc)[:120]

    keywords = [word for word in query.replace("，", " ").replace(",", " ").split() if word]
    return {
        "query": query,
        "keywords": keywords,
        "sources": sources,
        "source_count": len(sources),
        "provider": provider.provider,
    }


search_skill = SkillDefinition(
    name="search",
    category="research",
    description="收集与任务主题相关的资料线索，输出可复核的来源列表。",
    handler=_handler,
    input_schema={"query": "string", "limit": "integer?"},
    output_schema={"query": "string", "sources": "array", "source_count": "integer"},
)
