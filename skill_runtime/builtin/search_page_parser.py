"""Taobao search-result page parsers for market_research_web.

Two real page layouts observed live (2026-09-27):
  B: body collapses each listing onto one line:
     "¥1.00 1000+人收货 <title> <shop> <region>"
  C: price is split with spaces and sales uses 人付款:
     "21.99优惠后 2000+人付款 <title> <shop> <region>"
Parser splits listings by price tokens and maps buyers as observed sales.
"""

from __future__ import annotations

import re
from typing import Any

_PRICE_SPLIT_PAT = re.compile(r"[¥￥]\s*([0-9][0-9,]*)\s*(?:\.[0-9]{1,2})?")
_SALES_PAT = re.compile(r"([0-9,]+\+?)\s*人(?:收货|付款)(?:|([^\\n]{0,6}))")
_SHOP_PAT = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9]{2,24}(?:旗舰店|专卖店|专营店|美术馆|素材|小屋|小店|Studio|素材馆|设计|铺子|素材社|图书馆))"
)
_REGION_PAT = re.compile(r"(北京|上海|广东\s*广州|广东\s*深圳|浙江\s*杭州|江苏\s*苏州|湖北\s*武汉|湖北\s*十堰|河南\s*郑州|山东\s*济南|四川\s*成都|浙江\s*金华|安徽\s*合肥|福建\s*厦门|天津|重庆)")


def parse_search_page(text: str, keyword: str) -> list[dict[str, Any]]:
    """Parse both B/C layouts from one page text (no fabrication)."""
    rows: list[dict[str, Any]] = []
    if not text:
        return rows

    # Layout C: price uses space-separated decimals (`¥ 21 .99 2000+人付款 ...`)
    if "人付款" in text:
        rows = _parse_layout_c(text, keyword)
        if rows:
            return rows

    # Layout B fallback: single line with many `¥1.00` tokens
    for raw in text.splitlines():
        raw = (raw or "").strip()
        if not raw:
            continue
        matches = list(_PRICE_SPLIT_PAT.finditer(raw))
        if len(matches) <= 1:
            segment = raw
        else:
            starts = [m.start() for m in matches]
            for idx, start in enumerate(starts):
                end = starts[idx + 1] if idx + 1 < len(starts) else len(raw)
                rows.extend(_parse_layout_b(raw[start:end], keyword))
            continue
        rows.extend(_parse_layout_b(segment, keyword))
    return rows


def _parse_layout_b(line: str, keyword: str) -> list[dict[str, Any]]:
    m = _PRICE_SPLIT_PAT.search(line)
    if not m:
        return []
    try:
        price = float(m.group(1).replace(",", ""))
    except ValueError:
        return []
    rest = line[m.end() :].strip()
    buyers = None
    bm = _SALES_PAT.search(rest)
    if bm:
        digits = bm.group(1).replace(",", "").rstrip("+")
        buyers = int(digits) if digits.isdigit() else None
        rest = rest[bm.end() :].strip()
    after = _SHOP_PAT.search(rest)
    shop = None
    if after:
        shop = after.group(1)
        rest = rest[: after.start()].strip()
    _region = None
    rm = _REGION_PAT.search(rest)
    if rm:
        _region = rm.group(1)
    title = rest.strip(" |-—·")
    if len(title) < 4:
        return []
    region = _region
    return [
        {
            "title": title[:120],
            "price": price,
            "sales": buyers,
            "reviews": None,
            "shop": shop,
            "url": None,
            "region": region,
            "category": keyword,
            "observed_sales": buyers is not None,
        }
    ]


def _pick_title(body: str) -> str:
    """body order observed: <shop titles/region flags> <title> (everything up
    to next ¥). Title is the tail after the LAST known shop/flag token."""
    flags = re.compile(r"包邮|24小时内发|官方立减|公益宝贝|超级立减|实付低价自动发货|回头客\d+万?|优惠后")
    parts = flags.split(body)
    candidate = parts[-1].strip(" |-—·")
    shop_m = _SHOP_PAT.search(candidate)
    if shop_m:
        # candidate itself begins with shop? strip it too
        if shop_m.end() <= 8 and len(candidate) > 8:
            candidate = candidate[shop_m.end() :].strip(" |-—·")
    region_m = _REGION_PAT.search(candidate)
    if region_m and region_m.start() > 8:
        candidate = candidate[: region_m.start()].strip(" |-—·")
    return candidate[:120]


def _parse_layout_c(text: str, keyword: str) -> list[dict[str, Any]]:
    """Layout C: `price + (优惠后)? + <sales>人付款 + <title> ... <shop> ...`."""
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"([¥￥])\s*([0-9]+(?:\s*\.[0-9]{1,2})?)\s*(?:优惠后\s*)?"
        r"([0-9]+\+?)人付款\s+(.+?)(?=[¥￥]|\Z)",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        price_token = match.group(2).replace(" ", "")
        try:
            price = float(price_token.replace(",", ""))
        except ValueError:
            continue
        digits = match.group(3).replace(",", "").rstrip("+")
        buyers = int(digits) if digits.isdigit() else None
        body = match.group(4)
        shop = None
        shop_m = _SHOP_PAT.search(body)
        if shop_m:
            shop = shop_m.group(1)
        region_m = _REGION_PAT.search(body)
        region = region_m.group(1) if region_m else None  # noqa: F841
        title = _pick_title(body)
        if len(title) < 6:
            continue
        rows.append(
            {
                "title": title[:120],
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
