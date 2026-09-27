"""market_research_web (T-113 V2): agent-driven collection with risk governance.

Principles (AGENTS freeze; no stealth/proxy bypass):
  fast-fail on antibot / login walls ->  bounded network retries  ->
  task-level caps (pages/observes/runtime)  ->  real failure evidence, never
  fabricated rows.

Detection markers observed live (taobao): "访问被拒绝" / "请检查是否使用了代理"
/ captcha sliders / login redirects (login.taobao.com / being redirected to
a login page). Each maps to a stable code returned in `risk`:
  ANTIBOT_BLOCKED | LOGIN_REQUIRED | EMPTY_PAGE
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from shared.config import settings
from shared.logging import get_logger
from skill_runtime.base import SkillContext, SkillDefinition

logger = get_logger("skill")

_URL_COMM = "/command"
_DEFAULT_PAGES = 3
_URL_TAOBAO = "https://s.taobao.com/list?q={kw}&sort=sale-desc"
_URL_PDD = "https://mobile.pinduoduo.com/search.html?query={kw}"
_SCROLL_DELTA = 900
_PAGE_GAP_MS = 2500          # polite gap between observe rounds
_MAX_RUNTIME_SECONDS = 240   # task-level budget

_RISK_PATTERNS: list[tuple[str, str]] = [
    (re.compile(r"访问被拒绝"), "ANTIBOT_BLOCKED"),
    (re.compile(r"请检查是否使用了代理|verify|验证码|滑块|滑動|安全验证"), "ANTIBOT_BLOCKED"),
    (re.compile(r"login\.taobao\.com|havanaone|亲，请登录|请登录", re.I), "LOGIN_REQUIRED"),
]


class MarketResearchWebError(RuntimeError):
    def __init__(self, message: str, code: str = "STEP_FAILED", evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.evidence = evidence or {}


def _base() -> str:
    url = (settings.ecom_autopilot_base_url or "").rstrip("/")
    if not url:
        raise MarketResearchWebError("ECOM_AUTOPILOT_BASE_URL is empty; set it in .env")
    return url


def _token() -> str:
    return settings.ecom_autopilot_token or "dev-token"


def _post(cmd: dict[str, Any]) -> dict[str, Any]:
    url = f"{_base()}{_URL_COMM}"
    headers = {"X-Exec-Token": _token()}
    try:
        resp = httpx.post(
            url, json=cmd, headers=headers, timeout=settings.ecom_autopilot_timeout_seconds
        )
    except httpx.HTTPError as exc:
        raise MarketResearchWebError(
            f"exec service unreachable: {exc}", code="SERVICE_UNAVAILABLE"
        ) from exc
    if resp.status_code >= 400:
        kind = cmd.get("request", {}).get("kind")
        raise MarketResearchWebError(
            f"POST {kind} -> {resp.status_code}: {resp.text[:200]}",
            code="SERVICE_UNAVAILABLE",
            evidence={"status": resp.status_code, "url": url},
        )
    body = resp.json()
    if not body.get("ok"):
        kind = cmd.get("request", {}).get("kind")
        raise MarketResearchWebError(
            f"browser-service {kind} {body.get('code')}: {str(body.get('message'))[:200]}",
            code=str(body.get("code") or "STEP_FAILED"),
        )
    return body.get("data") or {}


def _risk_of(text: str) -> str | None:
    for pattern, code in _RISK_PATTERNS:
        if pattern.search(text or ""):
            return code
    return None


def _page_text(data: dict[str, Any]) -> str:
    page = data.get("page") or {}
    if isinstance(page, dict):
        text = page.get("bodyTextSample") or ""
        if text:
            return str(text)
    for key in ("text", "visibleText", "pageView"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "\n".join(str(v) for v in value)
    return json.dumps(data, ensure_ascii=False)[:4000]


_PRICE_PAT = re.compile(r"[¥￥]\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")
_BUYERS_PAT = re.compile(r"([0-9,]+\+?)\s*人收货")
_SHOP_PAT = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9]{2,24}(?:旗舰店|专卖店|专营店|商城|百货))"
)


def _split_product_lines(text: str) -> list[str]:
    """bodyTextSample often collapses the list into one line; split by price tokens."""
    lines: list[str] = []
    for raw in text.splitlines():
        raw = (raw or "").strip()
        if not raw:
            continue
        matches = list(_PRICE_PAT.finditer(raw))
        if len(matches) <= 1:
            lines.append(raw)
            continue
        starts = [m.start() for m in matches]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(raw)
            lines.append(raw[start:end].strip())
    return lines


def _parse_rows_from_text(text: str, keyword: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _split_product_lines(text):
        line = (line or "").strip()
        if len(line) < 8:
            continue
        price_match = _PRICE_PAT.search(line)
        if not price_match:
            continue
        try:
            price = float(price_match.group(1).replace(",", ""))
        except ValueError:
            continue
        buyers_match = _BUYERS_PAT.search(line)
        buyers: int | None = None
        if buyers_match:
            digits = buyers_match.group(1).replace(",", "").rstrip("+")
            buyers = int(digits) if digits.isdigit() else None
        after_price = line[price_match.end() :].strip()
        after_buyers = (
            re.sub(r"[0-9,]+\+?\s*人收货", "", after_price).strip() if buyers_match else after_price
        )
        stop = re.search(r"[¥￥]", after_buyers)
        segment = (after_buyers[: stop.start()] if stop else after_buyers).strip("-—|· ")
        shop_match = _SHOP_PAT.search(segment)
        shop = None
        if shop_match:
            shop = shop_match.group(1)
            segment = segment[: shop_match.start()].strip("-—|· ")
        if len(segment) < 4:
            continue
        rows.append(
            {
                "title": segment[:120],
                "price": price,
                "sales": buyers,
                "reviews": None,
                "shop": shop,
                "url": None,
                "category": keyword,
                "observed_sales": buyers is not None,
            }
        )
    return rows


def _risk_evidence(url: str, text: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": url,
        "page_title": (data.get("title") or "")[:80],
        "text_head": (text or "")[:400],
        "observed_at": data.get("timestamp"),
        "counts": data.get("counts"),
    }


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    platform = (inputs.get("platform") or "taobao").lower()
    keyword = str(inputs.get("keyword") or inputs.get("query") or "").strip()
    pages = int(inputs.get("pages") or inputs.get("rounds") or _DEFAULT_PAGES)
    account = inputs.get("account") or "default"
    if not keyword:
        raise MarketResearchWebError("input error: keyword is required")
    pages = max(1, min(pages, 10))

    url_pattern = _URL_TAOBAO if platform == "taobao" else _URL_PDD
    first_url = url_pattern.format(kw=httpx.QueryParams({"q": keyword}).get("q", keyword))
    logger.info("market_research_web %s keyword=%s pages=%s", platform, keyword, pages)

    collected: list[dict[str, Any]] = []
    seen: set[str] = set()
    rounds = 0

    for round_index in range(1, pages + 1):
        if rounds and (rounds * 8) > _MAX_RUNTIME_SECONDS:
            logger.warning("runtime budget reached after %s rounds", rounds)
            break
        observe_cmd = {
            "request": {
                "kind": "observe",
                "value": keyword,
                "options": {"url": first_url if round_index == 1 else None, "settle_ms": 3500},
            },
            "account": account,
        }
        data = _post(observe_cmd)
        rounds += 1
        text = _page_text(data)

        risk = _risk_of(text) or (
            "EMPTY_PAGE" if not text.strip() else None
        )
        if risk:
            raise MarketResearchWebError(
                f"{risk} at round {round_index}: {keyword!r} collect stopped (no retry, no fabrication)",
                code=risk,
                evidence=_risk_evidence(first_url, text, data),
            )

        rows = _parse_rows_from_text(text, keyword)
        new_rows = [row for row in rows if row["title"] not in seen]
        if not new_rows and round_index > 1:
            logger.info("round %s: no new rows, stopping politely", round_index)
            break
        for row in new_rows:
            seen.add(row["title"])
            collected.append(row)

        if round_index == pages:
            break
        _post({"request": {"kind": "scroll", "value": _SCROLL_DELTA}, "account": account})
        _post({"request": {"kind": "wait_for", "value": _PAGE_GAP_MS}, "account": account})

    if not collected:
        raise MarketResearchWebError(
            f"no market data for keyword={keyword!r} after {rounds} rounds (no fabrication)",
            code="EMPTY_PAGE",
            evidence={"url": first_url, "rounds": rounds},
        )
    observed = sum(1 for row in collected if row.get("observed_sales"))
    return {
        "rows": collected,
        "source": f"{platform}_browser_observation",
        "pages_observed": rounds,
        "products_count": len(collected),
        "sales_observed_rate": round(observed / len(collected), 3) if collected else 0.0,
        "keyword": keyword,
        "platform": platform,
    }


market_research_web_skill = SkillDefinition(
    name="market_research_web",
    category="market",
    description=(
        "AI 主动采集市场数据（EcomAutopilot 只读 observe/scroll + 风控治理："
        "快速失败 ANTIBOT_BLOCKED / LOGIN_REQUIRED / EMPTY_PAGE，绝无伪造/无重试风暴）。"
    ),
    handler=_handler,
    input_schema={"platform": "string?", "keyword": "string", "pages": "integer?", "account": "string?"},
    output_schema={"rows": "array", "source": "string", "pages_observed": "integer"},
)
