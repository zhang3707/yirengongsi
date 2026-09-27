"""Tests for market_evidence.py — 多源市场数据统一模型与采集器注册表（T-113a）"""

import pytest

from skill_runtime.builtin.market_evidence import (
    DataSourceError,
    DataSourceRegistry,
    MarketEvidence,
    ProductInfo,
    ProductMetrics,
    RawEvidence,
    evidences_to_rows,
    normalize_keyword,
)


def test_market_evidence_to_dict():
    """MarketEvidence 可以序列化为字典"""
    ev = MarketEvidence(
        source="taobao",
        evidence_type="observed",
        product=ProductInfo(name="PPT模板", price=19.9, platform="taobao"),
        metrics=ProductMetrics(sales=1832, reviews=860),
    )
    data = ev.to_dict()
    assert data["source"] == "taobao"
    assert data["evidence_type"] == "observed"
    assert data["product"]["name"] == "PPT模板"
    assert data["product"]["price"] == 19.9
    assert data["metrics"]["sales"] == 1832
    assert data["metrics"]["reviews"] == 860
    assert "collected_at" in data


def test_market_evidence_to_row():
    """MarketEvidence 可以转换为现有 market_analysis 期望的 rows 格式"""
    ev = MarketEvidence(
        source="taobao",
        evidence_type="observed",
        product=ProductInfo(
            name="PPT模板",
            price=19.9,
            category="虚拟商品",
            url="https://item.taobao.com/123",
            shop="某某旗舰店",
            platform="taobao"
        ),
        metrics=ProductMetrics(sales=1832, reviews=860),
    )
    row = ev.to_row()
    assert row["title"] == "PPT模板"
    assert row["price"] == 19.9
    assert row["sales"] == 1832
    assert row["reviews"] == 860
    assert row["category"] == "虚拟商品"
    assert row["shop"] == "某某旗舰店"
    assert row["url"] == "https://item.taobao.com/123"
    assert row["platform"] == "taobao"
    assert row["source"] == "taobao"
    assert row["evidence_type"] == "observed"


def test_evidences_to_rows():
    """evidences_to_rows 批量转换"""
    evs = [
        MarketEvidence(
            source="taobao",
            evidence_type="observed",
            product=ProductInfo(name=f"商品{i}", price=10.0 + i),
            metrics=ProductMetrics(sales=100 + i),
        )
        for i in range(3)
    ]
    rows = evidences_to_rows(evs)
    assert len(rows) == 3
    assert rows[0]["title"] == "商品0"
    assert rows[1]["price"] == 11.0
    assert rows[2]["sales"] == 102


class MockDataSource:
    """测试用数据源"""
    def __init__(self, name: str, evidences: list | None = None, error: Exception | None = None):
        self.name = name
        self.evidences = evidences or []
        self.error = error
    
    async def fetch(self, keyword: str, **kwargs) -> list:
        if self.error:
            raise self.error
        return self.evidences


@pytest.mark.asyncio
async def test_registry_fetch_all_success():
    """注册表可以从多个数据源获取数据并融合"""
    registry = DataSourceRegistry()
    
    ev1 = MarketEvidence(
        source="taobao",
        evidence_type="observed",
        product=ProductInfo(name="PPT模板", price=19.9, url="https://item.taobao.com/123"),
        metrics=ProductMetrics(sales=1832),
    )
    ev2 = MarketEvidence(
        source="reddit",
        evidence_type="api",
        product=ProductInfo(name="PPT Template", price=29.9, url="https://reddit.com/r/dropship/abc"),
        metrics=ProductMetrics(engagement=450),
    )
    
    registry.register(MockDataSource("taobao", evidences=[ev1]))
    registry.register(MockDataSource("reddit", evidences=[ev2]))
    
    evidences, errors = await registry.fetch_all(["taobao", "reddit"], keyword="PPT")
    
    assert len(evidences) == 2
    assert len(errors) == 0
    assert evidences[0].product.name == "PPT模板"
    assert evidences[1].product.name == "PPT Template"


@pytest.mark.asyncio
async def test_registry_fetch_all_partial_failure():
    """部分数据源失败时，成功的数据源仍然返回数据"""
    registry = DataSourceRegistry()
    
    ev1 = MarketEvidence(
        source="taobao",
        evidence_type="observed",
        product=ProductInfo(name="PPT模板", price=19.9),
        metrics=ProductMetrics(sales=1832),
    )
    
    registry.register(MockDataSource("taobao", evidences=[ev1]))
    registry.register(MockDataSource("pdd", error=DataSourceError("ANTIBOT_BLOCKED", code="ANTIBOT_BLOCKED")))
    
    evidences, errors = await registry.fetch_all(["taobao", "pdd"], keyword="PPT")
    
    assert len(evidences) == 1
    assert len(errors) == 1
    assert evidences[0].product.name == "PPT模板"
    assert errors[0]["source"] == "pdd"
    assert errors[0]["code"] == "ANTIBOT_BLOCKED"


@pytest.mark.asyncio
async def test_registry_fetch_all_all_failed():
    """所有数据源都失败时，返回空列表 + 错误列表"""
    registry = DataSourceRegistry()
    
    registry.register(MockDataSource("taobao", error=DataSourceError("ANTIBOT_BLOCKED", code="ANTIBOT_BLOCKED")))
    registry.register(MockDataSource("pdd", error=DataSourceError("LOGIN_REQUIRED", code="LOGIN_REQUIRED")))
    
    evidences, errors = await registry.fetch_all(["taobao", "pdd"], keyword="PPT")
    
    assert len(evidences) == 0
    assert len(errors) == 2
    assert errors[0]["code"] == "ANTIBOT_BLOCKED"
    assert errors[1]["code"] == "LOGIN_REQUIRED"


@pytest.mark.asyncio
async def test_registry_merge_evidences_dedup():
    """融合时按 URL 去重"""
    registry = DataSourceRegistry()
    
    # 同一商品被两个源采集到
    ev1 = MarketEvidence(
        source="taobao",
        evidence_type="observed",
        product=ProductInfo(name="PPT模板", price=19.9, url="https://item.taobao.com/123"),
        metrics=ProductMetrics(sales=1832, reviews=860),
    )
    ev2 = MarketEvidence(
        source="pdd",
        evidence_type="observed",
        product=ProductInfo(name="PPT模板", price=18.9, url="https://item.taobao.com/123"),
        metrics=ProductMetrics(sales=1500, rating=4.8),
    )
    
    registry.register(MockDataSource("taobao", evidences=[ev1]))
    registry.register(MockDataSource("pdd", evidences=[ev2]))
    
    evidences, errors = await registry.fetch_all(["taobao", "pdd"], keyword="PPT")
    
    assert len(evidences) == 1  # 去重后只剩 1 个
    assert len(errors) == 0
    
    merged = evidences[0]
    assert merged.source == "pdd+taobao"  # 来源合并
    assert merged.metrics.sales == 1832  # 取最大值
    assert merged.metrics.reviews == 860
    assert merged.metrics.rating == 4.8


@pytest.mark.asyncio
async def test_registry_merge_evidences_no_url():
    """无 URL 的证据不去重"""
    registry = DataSourceRegistry()
    
    ev1 = MarketEvidence(
        source="manual_import",
        evidence_type="manual",
        product=ProductInfo(name="PPT模板A", price=19.9, url=""),
        metrics=ProductMetrics(sales=1832),
    )
    ev2 = MarketEvidence(
        source="manual_import",
        evidence_type="manual",
        product=ProductInfo(name="PPT模板B", price=29.9, url=""),
        metrics=ProductMetrics(sales=2000),
    )
    
    registry.register(MockDataSource("manual_import", evidences=[ev1, ev2]))
    
    evidences, errors = await registry.fetch_all(["manual_import"], keyword="PPT")
    
    assert len(evidences) == 2  # 不去重
    assert len(errors) == 0


def test_normalize_keyword():
    """关键词标准化"""
    assert normalize_keyword("  PPT模板  ") == "ppt模板"
    assert normalize_keyword("PPT  模板") == "ppt 模板"
    assert normalize_keyword("PPT\t模板\n") == "ppt 模板"
