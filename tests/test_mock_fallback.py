"""Tests for T-113c: Mock 回退机制"""

import pytest

from skill_runtime.builtin.market_evidence import (
    DataSourceError,
    DataSourceRegistry,
    MarketEvidence,
    ProductInfo,
    ProductMetrics,
)
from skill_runtime.builtin.market_sources import MockDataSource


class FailingDataSource:
    """总是失败的数据源（测试用）"""

    def __init__(self, name: str):
        self.name = name

    async def fetch(self, keyword: str, **kwargs):
        raise DataSourceError(f"{self.name} failed", code="ANTIBOT_BLOCKED")


@pytest.mark.asyncio
async def test_mock_fallback_disabled_by_default():
    """Mock 回退默认关闭"""
    registry = DataSourceRegistry()
    registry.register(FailingDataSource("taobao"))
    registry.register(MockDataSource())

    evidences, errors = await registry.fetch_all(
        ["taobao"], keyword="PPT", allow_mock_fallback=False
    )

    assert len(evidences) == 0
    assert len(errors) == 1
    assert errors[0]["code"] == "ANTIBOT_BLOCKED"


@pytest.mark.asyncio
async def test_mock_fallback_enabled():
    """Mock 回退启用时，所有真实源失败后使用 Mock 数据"""
    registry = DataSourceRegistry()
    registry.register(FailingDataSource("taobao"))
    registry.register(MockDataSource())

    evidences, errors = await registry.fetch_all(
        ["taobao"], keyword="PPT", allow_mock_fallback=True
    )

    assert len(evidences) > 0
    assert errors[0]["code"] == "ANTIBOT_BLOCKED"
    assert errors[-1]["code"] == "MOCK_FALLBACK"
    assert all(ev.evidence_type == "mock" for ev in evidences)
    assert all(ev.source == "mock" for ev in evidences)


@pytest.mark.asyncio
async def test_mock_fallback_not_used_when_real_source_succeeds():
    """真实源成功时，不使用 Mock 回退"""

    class SuccessDataSource:
        name = "taobao"

        async def fetch(self, keyword: str, **kwargs):
            return [
                MarketEvidence(
                    source="taobao",
                    evidence_type="observed",
                    product=ProductInfo(name="真实商品", price=19.9),
                    metrics=ProductMetrics(sales=1000),
                )
            ]

    registry = DataSourceRegistry()
    registry.register(SuccessDataSource())
    registry.register(MockDataSource())

    evidences, errors = await registry.fetch_all(
        ["taobao"], keyword="PPT", allow_mock_fallback=True
    )

    assert len(evidences) == 1
    assert evidences[0].source == "taobao"
    assert evidences[0].evidence_type == "observed"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_mock_data_source_generates_valid_evidence():
    """MockDataSource 生成的数据符合 MarketEvidence Schema"""
    source = MockDataSource()
    evidences = await source.fetch(keyword="PPT", limit=5)

    assert len(evidences) == 5
    for ev in evidences:
        assert ev.source == "mock"
        assert ev.evidence_type == "mock"
        assert ev.product.name.startswith("Mock商品-PPT-")
        assert ev.product.price > 0
        assert ev.metrics.sales > 0
        assert ev.metrics.reviews > 0
        assert ev.product.url.startswith("https://mock.example.com/item/")
