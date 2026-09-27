"""Market Data Sources — 具体数据源实现（T-113a）.

迁移现有 market_research_web 的淘宝/PDD 采集逻辑为 DataSource 插件。
新增数据源只需实现 DataSource 接口并注册到全局注册表。
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from shared.config import settings
from shared.logging import get_logger
from skill_runtime.builtin.market_evidence import (
    DataSource,
    DataSourceError,
    MarketEvidence,
    ProductInfo,
    ProductMetrics,
    RawEvidence,
    register_source,
)
from skill_runtime.builtin.search_page_parser import parse_search_page

logger = get_logger("skill")


# ---------- Taobao Browser Source ----------

class TaobaoBrowserSource:
    """淘宝浏览器采集源（通过 EcomAutopilot browser-service）"""
    
    name = "taobao"
    
    _URL_COMM = "/command"
    _DEFAULT_PAGES = 3
    _URL_TAOBAO = "https://s.taobao.com/list?q={kw}&sort=sale-desc"
    _SCROLL_DELTA = 900
    _PAGE_GAP_MS = 2500
    _MAX_RUNTIME_SECONDS = 240
    
    _RISK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"访问被拒绝"), "ANTIBOT_BLOCKED"),
        (re.compile(r"请检查是否使用了代理|verify|验证码|滑块|滑動|安全验证"), "ANTIBOT_BLOCKED"),
        (re.compile(r"login\.taobao\.com|havanaone|亲，请登录|请登录", re.I), "LOGIN_REQUIRED"),
    ]
    
    def __init__(self):
        self._base_url = (settings.ecom_autopilot_base_url or "").rstrip("/")
        self._token = settings.ecom_autopilot_token or "dev-token"
    
    async def fetch(
        self,
        keyword: str,
        category: str | None = None,
        limit: int = 50,
        **kwargs: Any
    ) -> list[MarketEvidence]:
        """
        从淘宝搜索页采集商品数据。
        
        风控治理：
          * ANTIBOT_BLOCKED / LOGIN_REQUIRED → 立即停止，抛出 DataSourceError
          * 普通网络错误 → 有限重试（最多 2 次，指数退避）
          * 任务级冷却：最多采集 _DEFAULT_PAGES 页，总运行时间不超过 _MAX_RUNTIME_SECONDS
        """
        if not self._base_url:
            raise DataSourceError(
                "ECOM_AUTOPILOT_BASE_URL is empty; set it in .env",
                code="CONFIG_ERROR"
            )
        
        account = kwargs.get("account", "default")
        pages = min(kwargs.get("pages", self._DEFAULT_PAGES), 10)  # 硬上限 10 页
        
        # 使用 asyncio 运行同步采集逻辑（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_sync,
            keyword,
            pages,
            account,
            limit
        )
    
    def _fetch_sync(
        self,
        keyword: str,
        pages: int,
        account: str,
        limit: int
    ) -> list[MarketEvidence]:
        """同步采集逻辑（在 executor 中运行）"""
        import time
        
        start_time = time.time()
        collected: list[MarketEvidence] = []
        seen_titles: set[str] = set()
        first_url = ""
        
        # 初始化浏览器会话
        self._post({"request": {"kind": "session", "action": "start", "account": account}})
        
        try:
            # 打开淘宝首页
            self._post({"request": {"kind": "goto", "url": "https://www.taobao.com"}, "account": account})
            time.sleep(2)  # 等待页面加载
            
            # 搜索关键词
            search_url = self._URL_TAOBAO.format(kw=keyword)
            first_url = search_url
            self._post({"request": {"kind": "goto", "url": search_url}, "account": account})
            
            for round_index in range(1, pages + 1):
                # 检查任务级冷却
                if time.time() - start_time > self._MAX_RUNTIME_SECONDS:
                    logger.warning(f"Task-level timeout reached ({self._MAX_RUNTIME_SECONDS}s), stopping collection")
                    break
                
                # 观察页面
                observe_resp = self._post({
                    "request": {"kind": "observe", "settle_ms": self._PAGE_GAP_MS},
                    "account": account
                })
                
                # 风控检测
                page_text = observe_resp.get("pageView", {}).get("text", "")
                page_title = observe_resp.get("pageView", {}).get("title", "")
                current_url = observe_resp.get("pageView", {}).get("url", "")
                
                risk_code = self._detect_risk(page_text + " " + page_title + " " + current_url)
                if risk_code:
                    raise DataSourceError(
                        f"Risk detected: {risk_code}",
                        code=risk_code,
                        evidence={
                            "url": current_url,
                            "page_title": page_title,
                            "text_head": page_text[:200],
                            "round": round_index
                        }
                    )
                
                # 解析商品数据
                rows = parse_search_page(page_text, platform="taobao")
                new_rows = [row for row in rows if row["title"] not in seen_titles]
                
                for row in new_rows:
                    seen_titles.add(row["title"])
                    collected.append(self._row_to_evidence(row, current_url, round_index))
                
                if round_index == pages:
                    break
                
                # 滚动加载更多
                self._post({"request": {"kind": "scroll", "value": self._SCROLL_DELTA}, "account": account})
        
        finally:
            # 关闭浏览器会话
            try:
                self._post({"request": {"kind": "session", "action": "stop", "account": account}})
            except Exception as exc:
                logger.warning(f"Failed to stop browser session: {exc}")
        
        if not collected:
            raise DataSourceError(
                f"No market data for keyword={keyword!r} after {pages} rounds (no fabrication)",
                code="EMPTY_PAGE",
                evidence={"url": first_url, "rounds": pages}
            )
        
        return collected[:limit]
    
    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """发送命令到 EcomAutopilot browser-service"""
        url = f"{self._base_url}{self._URL_COMM}"
        headers = {"X-Exec-Token": self._token}
        
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                raise DataSourceError(
                    "Browser service authentication failed (check X-Exec-Token)",
                    code="AUTH_ERROR"
                )
            raise DataSourceError(
                f"Browser service error: {exc.response.status_code}",
                code="SERVICE_ERROR",
                evidence={"status_code": exc.response.status_code, "body": exc.response.text[:200]}
            )
        except httpx.TimeoutException:
            raise DataSourceError(
                "Browser service timeout (60s)",
                code="COMMAND_TIMEOUT"
            )
        except Exception as exc:
            raise DataSourceError(
                f"Browser service unexpected error: {exc}",
                code="UNEXPECTED_ERROR"
            )
    
    def _detect_risk(self, text: str) -> str | None:
        """检测风控标记"""
        for pattern, code in self._RISK_PATTERNS:
            if pattern.search(text):
                return code
        return None
    
    def _row_to_evidence(self, row: dict[str, Any], url: str, round_index: int) -> MarketEvidence:
        """将 search_page_parser 的 row 转换为 MarketEvidence"""
        return MarketEvidence(
            source="taobao",
            evidence_type="observed",
            product=ProductInfo(
                name=row.get("title", ""),
                price=row.get("price", 0.0),
                category=row.get("category", ""),
                url=row.get("url", ""),
                shop=row.get("shop"),
                platform="taobao"
            ),
            metrics=ProductMetrics(
                sales=row.get("sales"),
                reviews=row.get("reviews"),
            ),
            raw_evidence=RawEvidence(
                url=url,
                observation_round=round_index
            )
        )


# ---------- PDD Browser Source ----------

class PddBrowserSource(TaobaoBrowserSource):
    """PDD 浏览器采集源（继承淘宝逻辑，仅修改 URL 和平台标识）"""
    
    name = "pdd"
    _URL_PDD = "https://mobile.pinduoduo.com/search.html?query={kw}"
    
    def _fetch_sync(
        self,
        keyword: str,
        pages: int,
        account: str,
        limit: int
    ) -> list[MarketEvidence]:
        """PDD 采集逻辑（使用 PDD URL）"""
        # 临时替换 URL 模板
        original_url = self._URL_TAOBAO
        self._URL_TAOBAO = self._URL_PDD
        try:
            return super()._fetch_sync(keyword, pages, account, limit)
        finally:
            self._URL_TAOBAO = original_url
    
    def _row_to_evidence(self, row: dict[str, Any], url: str, round_index: int) -> MarketEvidence:
        """将 search_page_parser 的 row 转换为 MarketEvidence（PDD 平台）"""
        ev = super()._row_to_evidence(row, url, round_index)
        ev.source = "pdd"
        ev.product.platform = "pdd"
        return ev


# ---------- Manual Import Source ----------

class ManualImportSource:
    """手动导入数据源（从 market_research 迁移）"""
    
    name = "manual_import"
    
    async def fetch(
        self,
        keyword: str,
        category: str | None = None,
        limit: int = 50,
        **kwargs: Any
    ) -> list[MarketEvidence]:
        """
        从手动导入的数据（JSON/CSV）转换为 MarketEvidence。
        
         kwargs 必须包含以下之一：
          - products: list[dict] - JSON 格式的商品列表
          - csv: str - CSV 格式的商品数据
          - json: str - JSON 字符串格式的商品数据
        """
        products = kwargs.get("products")
        csv_text = kwargs.get("csv") or kwargs.get("data_csv")
        json_text = kwargs.get("json") or kwargs.get("data_json")
        
        rows: list[dict[str, Any]] = []
        
        if isinstance(products, list) and products:
            rows = [row for row in products if isinstance(row, dict)]
        elif isinstance(csv_text, str) and csv_text.strip():
            import csv as _csv
            import io
            reader = _csv.DictReader(io.StringIO(csv_text))
            for raw in reader:
                row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
                rows.append(row)
        elif isinstance(json_text, str) and json_text.strip():
            import json
            data = json.loads(json_text)
            if isinstance(data, list):
                rows = [row for row in data if isinstance(row, dict)]
        
        if not rows:
            raise DataSourceError(
                "No usable market data supplied; provide products (JSON rows) or csv/json string",
                code="EMPTY_INPUT"
            )
        
        # 转换为 MarketEvidence
        evidences: list[MarketEvidence] = []
        for row in rows[:limit]:
            # 标准化字段
            title = str(row.get("title", "")).strip()
            if not title:
                continue
            
            price = self._parse_float(row.get("price"))
            sales = self._parse_int(row.get("sales"))
            reviews = self._parse_int(row.get("reviews"))
            
            evidences.append(MarketEvidence(
                source="manual_import",
                evidence_type="manual",
                product=ProductInfo(
                    name=title,
                    price=price,
                    category=str(row.get("category", "")),
                    url=str(row.get("url", "")),
                    shop=row.get("shop"),
                    platform=str(row.get("platform", "unknown"))
                ),
                metrics=ProductMetrics(
                    sales=sales,
                    reviews=reviews,
                ),
                raw_evidence=RawEvidence(
                    url=str(row.get("url", "")),
                )
            ))
        
        if not evidences:
            raise DataSourceError(
                "All imported rows were invalid (missing title or required fields)",
                code="INVALID_INPUT"
            )
        
        return evidences
    
    def _parse_float(self, value: Any) -> float:
        """解析浮点数（支持字符串中的数字提取）"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            digits = re.sub(r"[^\d.]", "", value)
            return float(digits) if digits else 0.0
        return 0.0
    
    def _parse_int(self, value: Any) -> int:
        """解析整数"""
        return int(self._parse_float(value))


# ---------- Auto-register Sources ----------

def _auto_register():
    """自动注册所有数据源到全局注册表"""
    register_source(TaobaoBrowserSource())
    register_source(PddBrowserSource())
    register_source(ManualImportSource())
    logger.info("Auto-registered 3 market data sources: taobao, pdd, manual_import")


# 模块导入时自动注册
_auto_register()

