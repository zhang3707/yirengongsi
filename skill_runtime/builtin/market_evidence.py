"""Market Evidence — 多源市场数据统一模型与采集器注册表（T-113a）.

设计文档：docs/market_evidence_schema.md

核心原则：
  * 采集层和分析层彻底解耦
  * 所有数据源输出统一的 MarketEvidence 格式
  * 插件式注册，新数据源只需实现 DataSource 接口
  * 风控治理：快速失败、有限退避、任务级冷却、保留真实证据、绝不伪造数据
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Protocol

from shared.logging import get_logger

logger = get_logger("skill")


# ---------- Market Evidence Schema ----------

@dataclass
class ProductInfo:
    """商品基本信息"""
    name: str
    price: float
    category: str = ""
    url: str = ""
    image_url: str | None = None
    shop: str | None = None
    platform: str = ""


@dataclass
class ProductMetrics:
    """商品指标（可能为 None，表示未观测到）"""
    sales: int | None = None
    reviews: int | None = None
    rating: float | None = None
    trend_score: float | None = None  # 0-100，来自 Google Trends 等
    engagement: int | None = None     # Reddit upvotes / HN points 等


@dataclass
class RawEvidence:
    """原始证据（用于审计）"""
    url: str
    page_title: str | None = None
    screenshot_path: str | None = None
    api_response: dict[str, Any] | None = None
    observation_round: int | None = None


@dataclass
class MarketEvidence:
    """市场证据统一模型"""
    source: str                      # 数据源标识（taobao/pdd/1688/google_trends/reddit/manual_import）
    evidence_type: str               # observed | estimated | api | manual
    product: ProductInfo
    metrics: ProductMetrics
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_evidence: RawEvidence | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return asdict(self)

    def to_row(self) -> dict[str, Any]:
        """转换为现有 market_analysis 期望的 rows 格式（向后兼容）"""
        return {
            "title": self.product.name,
            "price": self.product.price,
            "sales": self.metrics.sales or 0,
            "reviews": self.metrics.reviews or 0,
            "category": self.product.category,
            "shop": self.product.shop,
            "url": self.product.url,
            "platform": self.product.platform,
            "source": self.source,
            "evidence_type": self.evidence_type,
            "collected_at": self.collected_at,
        }


# ---------- Data Source Interface ----------

class DataSourceError(RuntimeError):
    """数据源错误基类"""
    def __init__(self, message: str, code: str = "SOURCE_ERROR", evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.evidence = evidence or {}


class DataSource(Protocol):
    """数据源接口（所有数据源必须实现）"""
    
    name: str  # 数据源标识（如 "taobao", "reddit", "google_trends"）
    
    async def fetch(
        self,
        keyword: str,
        category: str | None = None,
        limit: int = 50,
        **kwargs: Any
    ) -> list[MarketEvidence]:
        """
        获取市场数据，返回标准化的 MarketEvidence 列表。
        
        风控治理要求：
          * 检测到风控（ANTIBOT_BLOCKED / LOGIN_REQUIRED）立即停止，抛出 DataSourceError
          * 普通网络错误可以有限重试（最多 2 次，指数退避）
          * 不伪造数据：采集失败返回空列表 + 抛出 DataSourceError
        """
        ...


# ---------- Data Source Registry ----------

class DataSourceRegistry:
    """数据源注册表（插件式）"""
    
    def __init__(self):
        self._sources: dict[str, DataSource] = {}
    
    def register(self, source: DataSource) -> None:
        """注册数据源"""
        if not source.name:
            raise ValueError("DataSource must have a name")
        if source.name in self._sources:
            logger.warning(f"DataSource {source.name} already registered, overwriting")
        self._sources[source.name] = source
        logger.info(f"Registered data source: {source.name}")
    
    def get(self, name: str) -> DataSource | None:
        """获取数据源"""
        return self._sources.get(name)
    
    def list_sources(self) -> list[str]:
        """列出所有已注册的数据源"""
        return list(self._sources.keys())
    
    async def fetch_all(
        self,
        source_names: list[str],
        keyword: str,
        category: str | None = None,
        limit: int = 50,
        **kwargs: Any
    ) -> tuple[list[MarketEvidence], list[dict[str, Any]]]:
        """
        从多个数据源获取数据并融合。
        
        Returns:
            (evidences, errors): 成功的证据列表 + 失败的错误列表
        """
        all_evidences: list[MarketEvidence] = []
        errors: list[dict[str, Any]] = []
        
        for source_name in source_names:
            source = self.get(source_name)
            if not source:
                errors.append({
                    "source": source_name,
                    "error": f"DataSource not registered: {source_name}",
                    "code": "SOURCE_NOT_FOUND"
                })
                continue
            
            try:
                evidences = await source.fetch(keyword=keyword, category=category, limit=limit, **kwargs)
                all_evidences.extend(evidences)
                logger.info(f"Fetched {len(evidences)} evidences from {source_name}")
            except DataSourceError as exc:
                errors.append({
                    "source": source_name,
                    "error": str(exc),
                    "code": exc.code,
                    "evidence": exc.evidence
                })
                logger.warning(f"DataSource {source_name} failed: {exc.code} - {exc}")
            except Exception as exc:
                errors.append({
                    "source": source_name,
                    "error": str(exc),
                    "code": "UNEXPECTED_ERROR"
                })
                logger.error(f"DataSource {source_name} unexpected error: {exc}", exc_info=True)
        
        # 融合：去重 + 合并
        merged = self._merge_evidences(all_evidences)
        return merged, errors
    
    def _merge_evidences(self, evidences: list[MarketEvidence]) -> list[MarketEvidence]:
        """
        融合多个数据源的证据：
          1. 按 product.url 去重（同一商品可能被多个源采集到）
          2. 合并指标（取最新/最全的）
          3. 标记来源（source 字段保留所有来源，如 "taobao+reddit"）
        """
        by_url: dict[str, list[MarketEvidence]] = {}
        for ev in evidences:
            url = ev.product.url
            if not url:
                # 无 URL 的证据无法去重，直接保留
                by_url[f"__no_url_{id(ev)}"] = [ev]
                continue
            by_url.setdefault(url, []).append(ev)
        
        merged: list[MarketEvidence] = []
        for url, evs in by_url.items():
            if len(evs) == 1:
                merged.append(evs[0])
                continue
            
            # 合并多个源的证据
            base = evs[0]  # 以第一个为基础
            sources = sorted({ev.source for ev in evs})
            base.source = "+".join(sources)
            
            # 合并指标（取非 None 的最大值）
            for ev in evs[1:]:
                if ev.metrics.sales is not None:
                    base.metrics.sales = max(base.metrics.sales or 0, ev.metrics.sales)
                if ev.metrics.reviews is not None:
                    base.metrics.reviews = max(base.metrics.reviews or 0, ev.metrics.reviews)
                if ev.metrics.rating is not None:
                    base.metrics.rating = max(base.metrics.rating or 0.0, ev.metrics.rating)
                if ev.metrics.trend_score is not None:
                    base.metrics.trend_score = max(base.metrics.trend_score or 0.0, ev.metrics.trend_score)
                if ev.metrics.engagement is not None:
                    base.metrics.engagement = max(base.metrics.engagement or 0, ev.metrics.engagement)
            
            merged.append(base)
        
        return merged


# ---------- Global Registry ----------

_registry = DataSourceRegistry()


def get_registry() -> DataSourceRegistry:
    """获取全局数据源注册表"""
    return _registry


def register_source(source: DataSource) -> None:
    """注册数据源到全局注册表"""
    _registry.register(source)


# ---------- Helper Functions ----------

def evidences_to_rows(evidences: list[MarketEvidence]) -> list[dict[str, Any]]:
    """将 MarketEvidence 列表转换为现有 market_analysis 期望的 rows 格式"""
    return [ev.to_row() for ev in evidences]


def normalize_keyword(keyword: str) -> str:
    """标准化关键词（去除首尾空格、转换为小写）"""
    return re.sub(r"\s+", " ", keyword.strip().lower())

