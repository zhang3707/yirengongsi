"""T-113b: 真实无风控数据源（Google Trends RSS + Hacker News Algolia API）.

两条无风控公开数据链路：
  * GoogleTrendsSource: trends.google.com/trending/rss?geo={geo}
    - 公开 RSS，无需 key，无 CAPTCHA
    - 输出 trend_score（Google 热度，无销量/价格 — evidence_type=api）
    - keyword 参数用于筛选相关条目（支持空 keyword = 全量）

  * HackerNewsSource: hn.algolia.com/api/v1/search
    - 公开 Algolia API，无需 key
    - engagement = HN points
    - evidence_type=api
"""        # noqa: E501

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx

from shared.logging import get_logger
from skill_runtime.builtin.market_evidence import (
    DataSourceError,
    MarketEvidence,
    ProductInfo,
    ProductMetrics,
    RawEvidence,
    register_source,
)

logger = get_logger("skill")


class GoogleTrendsSource:
    """Google Trends 每日热搜（公开 RSS，无风控）"""

    name = "google_trends"
    URL = "https://trends.google.com/trending/rss?geo={geo}"
    GEO_DEFAULT = "US"
    _NS = {"ht": "https://trends.google.com/trending/rss"}

    def __init__(self, http_timeout: float = 15.0):
        self._timeout = http_timeout

    async def fetch(
        self, keyword: str, category: str | None = None, limit: int = 50, **kwargs: Any
    ) -> list[MarketEvidence]:
        geo = kwargs.get("geo", self.GEO_DEFAULT)
        url = self.URL.format(geo=geo)

        try:
            resp = httpx.get(url, timeout=self._timeout, headers={"User-Agent": "ai-company-mvp/0.1"})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise DataSourceError(
                f"Google Trends RSS fetch failed: {exc}", code="SOURCE_UNAVAILABLE"
            ) from exc

        try:
            root = ElementTree.fromstring(resp.content)
        except ElementTree.ParseError as exc:
            raise DataSourceError(
                f"Google Trends RSS parse failed: {exc}", code="PARSE_ERROR"
            ) from exc

        items = root.findall(".//item")
        if not items:
            raise DataSourceError(
                f"Google Trends RSS returned 0 items for geo={geo}", code="EMPTY_PAGE"
            )

        evidences: list[MarketEvidence] = []
        kw_lower = keyword.strip().lower() if keyword else ""
        for item in items:
            title_el = item.find("title")
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue
            # keyword 过滤（为空时不筛）
            if kw_lower and kw_lower not in title.lower():
                continue

            traffic_el = item.find("ht:approx_traffic", self._NS)
            traffic = self._parse_int(traffic_el.text) if traffic_el is not None else None
            news_url_el = item.find("ht:news_item_url", self._NS)
            news_url = (news_url_el.text or "").strip() if news_url_el is not None else ""
            pub_date_el = item.find("pubDate")
            pub_date = (pub_date_el.text or "").strip() if pub_date_el is not None else ""

            evidences.append(
                MarketEvidence(
                    source="google_trends",
                    evidence_type="api",
                    product=ProductInfo(
                        name=title,
                        price=0.0,  # 趋势类无价格概念
                        category=category or "trend",
                        url=news_url,
                        platform="google_trends",
                    ),
                    metrics=ProductMetrics(traffic=traffic),
                    raw_evidence=RawEvidence(url=url, api_response={"geo": geo, "pub_date": pub_date}),
                )
            )
            if len(evidences) >= limit:
                break

        if not evidences:
            raise DataSourceError(
                f"No Google Trends items matching keyword={keyword!r} (geo={geo})",
                code="EMPTY_PAGE",
            )

        logger.info(f"GoogleTrendsSource fetched {len(evidences)} trends (geo={geo})")
        return evidences

    @staticmethod
    def _parse_int(text: str | None) -> int | None:
        if not text:
            return None
        digits = re.sub(r"[^0-9]", "", text.replace(",", ""))
        return int(digits) if digits else None


class HackerNewsSource:
    """Hacker News 热帖（公开 Algolia API，无风控）"""

    name = "hacker_news"
    URL = "https://hn.algolia.com/api/v1/search"
    DEFAULT_QUERIES = ("ecommerce", "dropshipping", "product hunt")

    def __init__(self, http_timeout: float = 15.0):
        self._timeout = http_timeout

    async def fetch(
        self, keyword: str, category: str | None = None, limit: int = 50, **kwargs: Any
    ) -> list[MarketEvidence]:
        query = keyword.strip() or self.DEFAULT_QUERIES[0]
        try:
            resp = httpx.get(
                self.URL,
                params={"query": query, "tags": "story", "hitsPerPage": min(limit, 50)},
                timeout=self._timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise DataSourceError(
                f"HackerNews fetch failed: {exc}", code="SOURCE_UNAVAILABLE"
            ) from exc

        data = resp.json()
        hits = data.get("hits") or []
        if not hits:
            raise DataSourceError(
                f"HackerNews returned 0 hits for query={query!r}", code="EMPTY_PAGE"
            )

        evidences: list[MarketEvidence] = []
        for hit in hits:
            title = (hit.get("title") or "").strip()
            if not title:
                continue
            points = hit.get("points")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            evidences.append(
                MarketEvidence(
                    source="hacker_news",
                    evidence_type="api",
                    product=ProductInfo(
                        name=title,
                        price=0.0,
                        category=category or "discussion",
                        url=url,
                        platform="hacker_news",
                    ),
                    metrics=ProductMetrics(points=points),
                    raw_evidence=RawEvidence(
                        url=self.URL,
                        api_response={"objectID": hit.get("objectID"), "created_at": hit.get("created_at")},
                    ),
                )
            )
            if len(evidences) >= limit:
                break

        logger.info(f"HackerNewsSource fetched {len(evidences)} hits (query={query!r})")
        return evidences


def register_external_sources() -> None:
    """注册外部数据源（在模块导入时由 load_external_sources 调用）"""
    register_source(GoogleTrendsSource())
    register_source(HackerNewsSource())
    logger.info("T-113b: registered google_trends + hacker_news sources")
