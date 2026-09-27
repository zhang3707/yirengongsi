"""market_research_web (T-113 V1): AI-Agent-driven market data collection.

Flow (agent-driven, no hardcoded scraping script):
  observe (search page)  ->  parse rows  ->  scroll  ->  observe  ->  ...
  repeated up to `pages` rounds; stops early if page stops changing.

Contract:
  * Every call goes through EcomAutopilot /command (X-Exec-Token).
  * ONLY read-only kinds are used: observe / scroll / wait_for.
  * Hard caps: max rounds, per-round timeout, explicit failure codes.
  * NEVER fabricates mock data — if the browser yields nothing, fail loudly.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

import httpx

from shared.config import settings
from shared.logging import get_logger
from skill_runtime.base import SkillContext, SkillDefinition

logger = get_logger("skill")

_URL_COMM = "/command"

_ROUNDS_DEFAULT = 3
_SCROLL_DELTA = 900
_WAIT_MS_BETWEEN = 1200

# Search page per platform (driver by daemon's account profile)
_URL_TAOBAO = "https://s.taobao.com/list?q={kw}&sort=sale-desc"
_URL_PDD = "https://mobile.pinduoduo.com/search.html?query={kw}"


class MarketResearchWebError(RuntimeError):
    pass


def _base() -> str:
    url = (settings.ecom_autopilot_base_url or "").rstrip("/")
    if not url:
        raise MarketResearchWebError(
            "ECOM_AUTOPILOT_BASE_URL is empty; set it in .env before using this skill"
        )
    return url


def _token() -> str:
    return settings.ecom_autopilot_token or "dev-token"


def _post(cmd: dict[str, Any]) -> dict[str, Any]:
    url = f"{_base()}{_URL_COMM}"
    headers = {"X-Exec-Token": _token()}
    try:
        resp = httpx.post(url, json=cmd, headers=headers, timeout=settings.ecom_autopilot_timeout_seconds)
    except httpx.HTTPError as exc:
        raise MarketResearchWebError(f"exec service unreachable: {exc}") from exc
    if resp.status_code >= 400:
        raise MarketResearchWebError(f"POST {cmd['request']['kind']} -> {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    if not body.get("ok"):
        err = body.get("code") or "STEP_FAILED"
        raise MarketResearchWebError(f"browser-service {cmd['request']['kind']} {err}: {body.get('message', '')[:200]}")
    return body.get("data") or {}


def _page_view_text(page: Any) -> str:
    """Best-effort extraction of visible text / rows from operator pageView."""
    if isinstance(page, dict):
        # the operator (observe-light) may emit any of these shapes
        for key in ("text", "visibleText", "pageView", "rows"):
            value = page.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return "\n".join(str(v) for v in value)
        return json.dumps(page, ensure_ascii=False)[:4000]
    if isinstance(page, str):
        return page
    return ""


_SALE_TOKENS = ("月售", "销量", "已售", "付款")

def _parse_price(text: str) -> float | None:
    match = re.search(r"[¥￥\s]([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)
    if not match:
        return None
    try:
        return float(Decimal(match.group(1).replace(",", "")))
    except Exception:  # noqa: BLE001
        return None


def _parse_sales(text: str) -> int | None:
    match = re.search(r"(?:月售|销量|已售)\s*([0-9,]+)([万kK]?)", text)
    if not match:
        return None
    digits = match.group(1).replace(",", "")
    value = float(digits)
    suffix = match.group(2).lower()
    if suffix == "万":
        return int(value * 10000)
    if suffix == "k":
        return int(value * 1000)
    return int(value)


def _parse_rows_from_text(text: str, keyword: str) -> list[dict[str, Any]]:
    """Very light heuristic line-by-line parser of the search page.

    The operator's observe-light output is free text; we treat each line that
    has a price as a candidate row. If a line also contains a sales token we
    attach it. If a line produces no title we skip it (no fabrication).
    """
    rows: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = (raw_line or "").strip()
        if len(line) < 8:
            continue
        price = _parse_price(line)
        if price is None:
            continue
        sales = _parse_sales(line)
        if sales is None:
            # Do not fabricate sales if the page doesn't show them
            # — keep None and treat as 0 for scoring but mark observed=False
            sales = None
        title = line.split("¥", 1)[0].split("￥", 1)[0].strip("｜|-—· ")
        if len(title) < 4:
            continue
        rows.append({
            "title": title[:120],
            "price": price,
            "sales": sales,
            "reviews": None,
            "shop": None,
            "url": None,
            "category": keyword,
            "observed_sales": sales is not None,
        })
    return rows


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    platform = (inputs.get("platform") or "taobao").lower()
    keyword = str(inputs.get("keyword") or inputs.get("query") or "").strip()
    pages = int(inputs.get("pages") or inputs.get("rounds") or _ROUNDS_DEFAULT)
    account = inputs.get("account") or "default"
    if not keyword:
        raise MarketResearchWebError("input error: keyword is required")
    pages = max(1, min(pages, 10))

    url_pattern = _URL_TAOBAO if platform == "taobao" else _URL_PDD
    first_url = url_pattern.format(kw=httpx.QueryParams({"q": keyword}).get("q", keyword))

    logger.info("market_research_web %s keyword=%s pages=%s", platform, keyword, pages)

    collected: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    rounds_observed = 0

    for round_index in range(1, pages + 1):
        # --- observe current page ---
        observe_cmd = {
            "request": {
                "kind": "observe",
                "value": keyword,
                "options": {"url": first_url if round_index == 1 else None, "settle_ms": 1500},
            },
            "account": account,
        }
        data = _post(observe_cmd)
        rounds_observed += 1
        page_text = _page_view_text(data)
        if not page_text:
            logger.warning("round %s: no page text returned", round_index)
            break
        rows = _parse_rows_from_text(page_text, keyword)
        new_rows = [row for row in rows if row["title"] not in seen_titles]
        if not new_rows and round_index > 1:
            logger.info("round %s: no new rows, stopping early", round_index)
            break
        for row in new_rows:
            if row["title"] not in seen_titles:
                seen_titles.add(row["title"])
                collected.append(row)

        if round_index == pages:
            break
        # --- scroll to load next batch / page ---
        scroll_cmd = {
            "request": {"kind": "scroll", "value": _SCROLL_DELTA},
            "account": account,
        }
        _post(scroll_cmd)
        # wait a bit between (read-only pause; keeps human pace rule)
        wait_cmd = {"request": {"kind": "wait_for", "value": _WAIT_MS_BETWEEN}, "account": account}
        _post(wait_cmd)

    if not collected:
        raise MarketResearchWebError(
            f"no market data collected for keyword={keyword!r} after {rounds_observed} rounds;"
            " refusing to fabricate a report (possibly login required / antibot)"
        )

    observed_sales = sum(1 for row in collected if row.get("observed_sales"))
    return {
        "rows": collected,
        "source": f"{platform}_browser_observation",
        "pages_observed": rounds_observed,
        "products_count": len(collected),
        "sales_observed_rate": round(observed_sales / len(collected), 3) if collected else 0.0,
        "keyword": keyword,
        "platform": platform,
    }


market_research_web_skill = SkillDefinition(
    name="market_research_web",
    category="market",
    description=(
        "AI 主动采集市场数据（EcomAutopilot browser-service 只读 observe/scroll 循环）；"
        "输出标准化 rows。不编造销量，采集失败即失败。"
    ),
    handler=_handler,
    input_schema={"platform": "string?", "keyword": "string", "pages": "integer?", "account": "string?"},
    output_schema={"rows": "array", "source": "string", "pages_observed": "integer"},
)
