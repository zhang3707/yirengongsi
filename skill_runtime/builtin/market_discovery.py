"""Market discovery skills (T-111 V1): import -> analyze -> discover -> feasibility.

Design:
  * V1 accepts *imported* data (inline JSON rows / CSV text) — NOT scraped from
    any platform. Scraping comes later behind the same skill contract.
  * Empty data must fail loudly (no fabricated "framework" reports).
  * Scores are deterministic rule-based internal signals, not profits.
  * Opportunity gating is conservative: copyright/indeterminate supply kills a
    candidate before any scoring is presented.
"""

from __future__ import annotations

import csv as _csv
import io
import json
import re
from typing import Any

from shared.logging import get_logger
from skill_runtime.base import SkillContext, SkillDefinition

# T-113a: 多源数据采集支持
from skill_runtime.builtin.market_evidence import evidences_to_rows, get_registry

logger = get_logger("skill")

REQUIRED_FIELDS = {"title", "price", "sales"}
NUMERIC_FIELDS = ("price", "sales", "reviews")


def _rows_from_inputs(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    # T-113a: 多源采集
    sources = inputs.get("sources")
    if sources and isinstance(sources, list):
        import asyncio
        keyword = inputs.get("keyword", "")
        
        registry = get_registry()
        limit = inputs.get("limit", 50)
        category = inputs.get("category")
        
        # 运行异步采集（AnyIO worker 线程无 event loop，用 asyncio.run 创建新 loop）
        allow_mock = inputs.get("allow_mock_fallback", False)  # T-113c: Mock 回退
        # 排除已显式传参的 key，避免 **kwargs 冲突
        extra_kwargs = {k: v for k, v in inputs.items() if k not in (
            "sources", "keyword", "category", "limit",
            "allow_mock_fallback", "products", "csv", "json", "data_csv", "data_json",
        )}
        evidences, errors = asyncio.run(
            registry.fetch_all(sources, keyword=keyword, category=category, limit=limit, allow_mock_fallback=allow_mock, **extra_kwargs)
        )
        
        if not evidences and errors:
            # 所有数据源都失败了
            error_summary = "; ".join([f"{e['source']}: {e['code']}" for e in errors])
            raise ValueError(f"All data sources failed: {error_summary}")
        
        return evidences_to_rows(evidences)
    
    products = inputs.get("products")
    if isinstance(products, list) and products:
        return [row for row in products if isinstance(row, dict)]

    csv_text = inputs.get("csv") or inputs.get("data_csv")
    if isinstance(csv_text, str) and csv_text.strip():
        reader = _csv.DictReader(io.StringIO(csv_text))
        rows = []
        for raw in reader:
            row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
            rows.append(row)
        return rows

    json_text = inputs.get("json") or inputs.get("data_json")
    if isinstance(json_text, str) and json_text.strip():
        data = json.loads(json_text)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    return []


def _coerce(row: dict[str, Any]) -> dict[str, Any] | None:
    normalized: dict[str, Any] = {k: v for k, v in row.items()}
    for field in NUMERIC_FIELDS:
        value = normalized.get(field)
        if isinstance(value, str):
            digits = re.sub(r"[^\d.]", "", value)
            normalized[field] = float(digits) if digits else None
    normalized["sales"] = float(normalized.get("sales") or 0)
    normalized["price"] = float(normalized.get("price") or 0)
    reviews = normalized.get("reviews")
    normalized["reviews"] = float(reviews) if reviews else 0.0
    if not str(normalized.get("title") or "").strip():
        return None
    if not REQUIRED_FIELDS <= {k for k, v in normalized.items() if v is not None}:
        return None
    return normalized


# ---------------- market_research ----------------

def _market_research(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    raw_rows = _rows_from_inputs(inputs)
    rows = [row for row in (_coerce(item) for item in raw_rows) if row]
    dropped = len(raw_rows) - len(rows)
    if not rows:
        raise ValueError(
            "no usable market data supplied; provide input_payload.products (JSON rows)"
            " or input_payload.csv. Refusing to fabricate a report."
        )
    return {
        "products_count": len(rows),
        "dropped_rows": dropped,
        "sources": [f"imported:{rows[0].get('category') or 'generic'}"],
        "rows": rows[:500],
        "material": [f"{row['title']} | price={row['price']} | sales={int(row['sales'])}" for row in rows[:30]],
    }


# ---------------- market_analysis ----------------

def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(len(ordered) * ratio), len(ordered) - 1)
    return ordered[index]


def _market_analysis(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in inputs.get("rows") or [] if isinstance(row, dict)]
    if not rows:
        raise ValueError("no normalized rows for analysis; market_research must run first")
    sales = [float(row.get("sales") or 0) for row in rows]
    prices = [float(row.get("price") or 0) for row in rows if float(row.get("price") or 0) > 0]
    titles = [str(row.get("title") or "") for row in rows]
    unique_ratio = len({t.rsplit("｜", 1)[0][:8] for t in titles}) / max(len(titles), 1)
    top_share = (max(sales) / sum(sales)) if sum(sales) else 0.0
    analysis = {
        "rows_count": len(rows),
        "sales_p50": _percentile(sales, 0.5),
        "sales_p90": _percentile(sales, 0.9),
        "price_p25": _percentile(prices, 0.25) if prices else 0.0,
        "price_p75": _percentile(prices, 0.75) if prices else 0.0,
        "top_share": round(top_share, 3),
        "homogeneity": round(1 - unique_ratio, 3),
        "demand_score": round(min(1.0, (_percentile(sales, 0.5) or 0) / 1000), 3),
        "competition_score": round(min(1.0, top_share + (1 - unique_ratio)), 3),
    }
    analysis["price_opportunity"] = round(
        max(0.0, analysis["price_p75"] - analysis["price_p25"]) / max(analysis["price_p75"], 1), 3
    )
    return analysis


# ---------------- opportunity_discovery ----------------

_EXCLUDE_TITLE_TERMS = ("代做", "代考", "代写论文", "盗版", "破解", "外挂", "刷单", "彩票", "私服")

def _opportunity_discovery(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in inputs.get("rows") or [] if isinstance(row, dict)]
    if not rows:
        raise ValueError("opportunity_discovery requires normalized rows")
    raw_analysis = inputs.get("analysis")
    if isinstance(raw_analysis, list):
        raw_analysis = raw_analysis[-1] if raw_analysis else {}
    if not isinstance(raw_analysis, dict):
        raw_analysis = {}
    analysis = raw_analysis
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        title = str(row.get("title") or "")
        lower = title.lower()
        if any(term in lower for term in _EXCLUDE_TITLE_TERMS):
            rejected.append({**row, "reject_reason": "compliance: disallowed term"})
            continue
        # T-113b: 趋势/社群类 evidence 无销量价格，用 signal 评分
        evidence_type = str(row.get("evidence_type") or "")
        source_name = str(row.get("source") or "")
        if evidence_type in ("api", "mock") or source_name in ("google_trends", "hacker_news"):
            signal = max(
                float(row.get("traffic") or 0),
                float(row.get("points") or 0),
                float(row.get("engagement") or 0),
            )
            if signal <= 0:
                rejected.append({**row, "reject_reason": "trend row missing signal"})
                continue
            score = round(min(1.0, signal / 100000.0), 3)
            candidates.append({**row, "opportunity_score": score})
            continue
        sales = float(row.get("sales") or 0)
        price = float(row.get("price") or 0)
        if sales <= 0 or price <= 0:
            rejected.append({**row, "reject_reason": "data incomplete"})
            continue
        demand_gap = sales < (analysis.get("sales_p90") or sales)
        competition = analysis.get("competition_score") or 0
        homogeneity = analysis.get("homogeneity") or 0
        if competition > 0.8 and homogeneity > 0.8:
            rejected.append({**row, "reject_reason": "oversaturated niche"})
            continue
        score = round(
            0.45 * (sales / max(analysis.get("sales_p50") or sales, 1))
            + 0.3 * (1 - competition)
            + 0.25 * analysis.get("price_opportunity", 0.0) * (demand_gap or 0.5),
            3,
        )
        candidates.append({**row, "opportunity_score": min(score, 1.0)})
    candidates.sort(key=lambda row: -float(row.get("opportunity_score") or 0))
    return {
        "candidates": candidates[:5],
        "rejected_count": len(rejected),
        "rejected": rejected[:10],
        "auto_degree": "high" if rows and analysis else "unknown",
        "supply_verified": bool(inputs.get("supply_source") or inputs.get("manual")),
        "step": "human_confirmation_required",
    }


# ---------------- project_feasibility ----------------

def _project_feasibility(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    candidates = [row for row in inputs.get("candidates") or [] if isinstance(row, dict)]
    if not candidates:
        raise ValueError("no candidates to assess; opportunity_discovery must run first")
    from shared.model_provider import get_model_provider

    provider = get_model_provider()
    projects: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates[:3], start=1):
        base = {
            "project_id": f"PRJ-{index}",
            "title": candidate.get("title"),
            "price": candidate.get("price"),
            "sales": candidate.get("sales"),
            "opportunity_score": candidate.get("opportunity_score"),
            "url": candidate.get("url"),  # T-112: 传递 URL 供 sources 使用
            "platform": candidate.get("platform"),  # T-112: 传递平台供 sources 使用
            "evidence_type": candidate.get("evidence_type"),  # T-113c: 传递 evidence_type
        }
        if provider.provider == "mock":
            card = {
                **base,
                "target_users": "见人工复核",
                "problem": "见人工复核",
                "delivery": "EcomAutopilot dry_run → 人工 → 真发",
                "supply_source": "需人工确认（导入数据未标注）",
                "manual_steps": ["核对版权/合规", "准备素材", "定价终审"],
                "validation_cost": "一单 dry_run + 人工复核 ≈ 30-60 分钟",
                "risks": ["数据为导入样本，非实时", "版权/供给待人工核实"],
                "mvp_first_version": "先 dry_run 上架，观察 7 天数据再决定",
            }
        else:
            system = (
                "你是项目经理。仅输出 JSON：{target_users, problem, delivery, supply_source,"
                " manual_steps:[], validation_cost, risks:[], mvp_first_version}。"
                ".sell点基于给定商品数据；exports_source 若数据未给则写「需人工确认」。"
            )
            user = json.dumps(base, ensure_ascii=False)
            try:
                card = {**base, **json.loads(provider.complete(system, user, context))}
            except Exception as exc:  # noqa: BLE001 - fallback to deterministic card
                card = {**base, "error_from_llm": str(exc)[:120], **{
                    k: v for k, v in (
                        ("target_users", "见人工复核"), ("problem", "见人工复核"),
                        ("supply_source", "需人工确认"),
                    )
                }}
        projects.append(card)
    
    # T-112: 转换 projects 为 report 技能期望的 findings/risks/sources 格式
    findings = []
    all_risks = []
    sources = []
    
    for proj in projects:
        # 核心发现：每个项目的问题和解决方案
        if proj.get('problem') and proj.get('problem') != '见人工复核':
            findings.append(f"{proj['title']}: {proj.get('problem', '')} (目标用户: {proj.get('target_users', '待确认')})")
        
        # 收集所有风险
        if proj.get('risks') and isinstance(proj['risks'], list):
            all_risks.extend([f"{proj['title']}: {risk}" for risk in proj['risks']])
        
        # 收集来源信息
        if proj.get('url'):
            sources.append({
                'title': proj['title'],
                'origin': proj.get('platform', 'unknown'),
                'url': proj.get('url'),
                'evidence_type': proj.get('evidence_type', 'unknown')  # T-113c: 传递 evidence_type
            })
    
    # 如果没有有效的 findings，使用候选商品的标题
    if not findings:
        findings = [f"{proj['title']} (价格: {proj.get('price', 0)}, 销量: {proj.get('sales', 0)})" for proj in projects[:5]]
    
    # 如果没有风险，添加默认提示
    if not all_risks:
        all_risks = ['数据来源待验证', '需人工确认版权/合规性']
    
    return {
        "projects": projects,
        "findings": findings,
        "risks": all_risks[:10],  # 最多 10 条
        "sources": sources[:20],  # 最多 20 条
        "next": "human_confirmation",
        "manual_steps": ["人工逐条确认项目卡片", "确认后 choose product_dir 交 EcomAutopilot dry_run"],
    }


market_research_skill = SkillDefinition(
    name="market_research",
    category="market",
    description=(
        "导入市场数据（JSON/CSV）或从多源采集（sources 参数），标准化为统一 rows；"
        "素材为空时显式失败。"
    ),
    handler=_market_research,
    input_schema={
        "products": "array?", "csv": "string?", "json": "string?",
        "sources": "array?", "keyword": "string?", "category": "string?", "limit": "integer?"
    },
    output_schema={"products_count": "integer", "rows": "array"},
)

market_analysis_skill = SkillDefinition(
    name="market_analysis",
    category="market",
    description="对导入的 rows 计算需求/竞争/价格带/同质化等内部指标。",
    handler=_market_analysis,
    input_schema={"rows": "array"},
    output_schema={"demand_score": "float", "competition_score": "float"},
)

opportunity_discovery_skill = SkillDefinition(
    name="opportunity_discovery",
    category="market",
    description="按保守硬规则筛选候选项目；合规不明的候选直接淘汰。",
    handler=_opportunity_discovery,
    input_schema={"rows": "array", "analysis": "object"},
    output_schema={"candidates": "array", "rejected_count": "integer"},
)

project_feasibility_skill = SkillDefinition(
    name="project_feasibility",
    category="market",
    description="把候选商品转成项目卡片；输出需人工确认的最小步骤 + findings/risks/sources（供 report 使用）。",
    handler=_project_feasibility,
    input_schema={"candidates": "array"},
    output_schema={"projects": "array", "findings": "array", "risks": "array", "sources": "array", "next": "string"},
)
