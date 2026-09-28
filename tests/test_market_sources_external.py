"""T-113b tests: Google Trends + Hacker News 无风控数据源（真实网络测试）"""

import pytest

from skill_runtime.builtin.market_evidence import DataSourceError
from skill_runtime.builtin.market_sources_external import (
    GoogleTrendsSource,
    HackerNewsSource,
    register_external_sources,
)
from skill_runtime.builtin.market_evidence import get_registry


@pytest.mark.asyncio
async def test_google_trends_real_fetch():
    """真实网络：Google Trends RSS 返回热搜条目"""
    source = GoogleTrendsSource()
    evidences = await source.fetch(keyword="", limit=5)  # 空 keyword = 全量

    assert len(evidences) >= 1
    for ev in evidences:
        assert ev.source == "google_trends"
        assert ev.evidence_type == "api"
        assert ev.product.name
        assert ev.metrics.traffic is not None


@pytest.mark.asyncio
async def test_google_trends_keyword_filter():
    """keyword 过滤：匹配的条目才返回"""
    source = GoogleTrendsSource()
    # 先拿全量前 5，挑第 1 个的 title 片段作为过滤词
    all_data = await source.fetch(keyword="", limit=5)
    if not all_data:
        pytest.skip("trends returned nothing")
    sample = all_data[0].product.name[:4]
    filtered = await source.fetch(keyword=sample, limit=5)
    assert all(sample.upper() in ev.product.name.upper() for ev in filtered)
    assert len(filtered) >= 1


@pytest.mark.asyncio
async def test_hacker_news_real_fetch():
    """真实网络：HN Algolia API 返回热帖"""
    source = HackerNewsSource()
    evidences = await source.fetch(keyword="ecommerce", limit=5)

    assert len(evidences) >= 1
    for ev in evidences:
        assert ev.source == "hacker_news"
        assert ev.evidence_type == "api"
        assert ev.product.name
        assert ev.metrics.points is not None


@pytest.mark.asyncio
async def test_registry_multi_source_fusion():
    """多源融合：google_trends + hacker_news 并发获取"""
    register_external_sources()
    registry = get_registry()

    evidences, errors = await registry.fetch_all(
        ["google_trends", "hacker_news"], keyword="", limit=10
    )

    assert len(errors) == 0
    sources = {ev.source for ev in evidences}
    assert "google_trends" in sources
    assert "hacker_news" in sources
    assert len(evidences) >= 2


@pytest.mark.asyncio
async def test_mock_fallback_still_works_with_new_sources():
    """真实源 + Mock 兜底组合：真实源失败时 Mock 生效"""
    registry = get_registry()
    # 用一个不存在的源名触发失败，然后 mock 兜底
    evidences, errors = await registry.fetch_all(
        ["nonexistent_source"], keyword="PPT", limit=5, allow_mock_fallback=True
    )
    assert len(evidences) >= 1
    assert all(ev.evidence_type == "mock" for ev in evidences)
    assert errors[-1]["code"] == "MOCK_FALLBACK"
