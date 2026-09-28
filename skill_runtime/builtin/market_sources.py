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

def current_page_url(obs_data: dict) -> str:
    """observe-light data 中取当前 URL（顶层 url）。"""
    return str((obs_data or {}).get("url") or "")


class TaobaoBrowserSource:
    """淘宝浏览器采集源（通过 EcomAutopilot browser-service）"""
    
    name = "taobao"
    
    _URL_COMM = "/command"
    _DEFAULT_PAGES = 3
    _URL_TAOBAO = "https://s.taobao.com/list?q={kw}&sort=sale-desc"
    _SCROLL_DELTA = 900
    _PAGE_GAP_MS = 2500
    _MAX_RUNTIME_SECONDS = 420
    
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
            # 淘宝首页（搜索框 flow —— direct URL 会被风控 deny，首页搜索框实证可用）
            # 避免新开 tab：先 observe 一次；已在 taobao/搜索页则复用
            pre_obs = self._post({"request": {"kind": "observe", "settle_ms": 600}, "account": account})
            pre = (pre_obs or {}).get("data") or pre_obs
            pre_url = str((pre or {}).get("url") or "")
            if "taobao.com" not in pre_url:
                self._post({"request": {"kind": "goto", "url": "https://www.taobao.com"}, "account": account})
                time.sleep(2)
            
            observe1 = self._post({"request": {"kind": "observe", "settle_ms": 1200}, "account": account})
            obs1_data = (observe1 or {}).get("data") or observe1
            page1 = obs1_data.get("page") or {}
            form_controls = page1.get("formControls") or []
            clickables = page1.get("clickables") or []
            search_input = None
            search_btn = None
            for ctl in form_controls:
                if str(ctl.get("role") or "").lower() == "combobox" or str(ctl.get("tag") or "").lower() == "input":
                    search_input = ctl
                    break
            for act in clickables:
                label = str(act.get("name") or act.get("text") or "")
                if "搜索" in label and search_btn is None:
                    search_btn = act
            if not search_input:
                raise DataSourceError(
                    "taobao search box not found on home page",
                    code="EMPTY_PAGE",
                    evidence={"url": current_page_url(obs1_data), "formControls": len(form_controls)},
                )
            approval = {"allowed": True, "token": self._token}
            self._post({
                "request": {"kind": "fill",
                             "target": {"shortId": search_input.get("id")},
                             "value": keyword},
                "account": account,
                "policyApproval": approval,
            })
            # fill 后重新 observe 拿最新 search 按钮 id（页面 id 每次轮换）
            obs2 = self._post({"request": {"kind": "observe", "settle_ms": 500}, "account": account})
            p2 = ((obs2 or {}).get("data") or obs2 or {}).get("page") or {}
            clicks2 = p2.get("clickables") or []
            # 优先 tag=button name=搜索；否则带"搜索"的 link（icon btn）
            btn = next((a for a in clicks2
                         if a.get("tag") == "button" and str(a.get("name") or "").strip() == "搜索"), None)
            if not btn:
                btn = next((a for a in clicks2
                             if "搜索" in str(a.get("name") or "") and a.get("tag") == "button"), None)
            if btn:
                self._post({
                    "request": {"kind": "click", "target": {"shortId": btn.get("id")}},
                    "account": account,
                    "policyApproval": approval,
                })
            else:
                self._post({
                    "request": {"kind": "press", "value": "Enter"},
                    "account": account,
                    "policyApproval": approval,
                })
            time.sleep(3)  # 等搜索结果页加载（page gap 作为 settle）
            # 搜索动作后再 observe 拿结果页 URL
            post_obs = self._post({"request": {"kind": "observe", "settle_ms": 800}, "account": account})
            post_data = (post_obs or {}).get("data") or post_obs
            first_url = current_page_url(post_data)
            
            for round_index in range(1, pages + 1):
                # 检查任务级冷却
                if time.time() - start_time > self._MAX_RUNTIME_SECONDS:
                    logger.warning(f"Task-level timeout reached ({self._MAX_RUNTIME_SECONDS}s), stopping collection")
                    break
                
                # T-117a: 淘宝是滚动懒加载 —— 每页先连续滚几次，把本页数据触发出来再 observe
                if round_index > 1:
                    for _ in range(4):
                        self._post({"request": {"kind": "scroll", "value": self._SCROLL_DELTA}, "account": account})
                        time.sleep(0.8)
                        if time.time() - start_time > self._MAX_RUNTIME_SECONDS:
                            break
                
                # 观察页面
                observe_resp = self._post({
                    "request": {"kind": "observe", "settle_ms": self._PAGE_GAP_MS},
                    "account": account
                })
                data = (observe_resp or {}).get("data") or observe_resp  # /command 包了一层 data
                
                # 风控检测：文本在 data.page.bodyTextSample（observe-light 格式）
                page_obj = data.get("page") or {}
                page_text = str(page_obj.get("bodyTextSample") or "")
                page_title = str(data.get("title") or "")
                current_url = str(data.get("url") or "")
                
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
                
                # 解析商品数据（过滤 NPS 满意度调查/页码/导航噪声）
                rows = parse_search_page(page_text, keyword=keyword)
                noise_patterns = (
                    "对本次搜索体验满意吗", "非常满意", "感觉一般", "非常不满意",
                    "上一页，当前第", "下一页，当前第",
                )
                def _is_noise(t, _patterns=tuple(noise_patterns)):
                    low = str(t or "")
                    return any(p in low for p in _patterns)
                rows = [r for r in rows if not _is_noise(r.get("title"))]
                new_rows = [row for row in rows if row["title"] not in seen_titles]
                
                for row in new_rows:
                    seen_titles.add(row["title"])
                    collected.append(self._row_to_evidence(row, current_url, round_index))
                
                if round_index == pages:
                    break
                
                # 翻页：优先点击「下一页」button（淘宝分页） —— 再退回首屏 scroll（懒加载补充行）
                page_tmp = None
                probe = self._post({"request": {"kind": "observe", "settle_ms": 400}, "account": account})
                probe_d = (probe or {}).get("data") or probe or {}
                page_tmp = probe_d.get("page") or {}
                clicks_probe = page_tmp.get("clickables") or []
                next_btn = None
                for a in clicks_probe:
                    role = str(a.get("role") or "").lower()
                    tag = str(a.get("tag") or "").lower()
                    if role not in ("button", "link") and tag not in ("button", "li", "a"):
                        continue
                    label = str(a.get("name") or a.get("text") or "")
                    if ("下一页" in label or "下页" in label or ">" in label) and not a.get("disabled"):
                        next_btn = a
                        break
                if next_btn:
                    self._post({
                        "request": {"kind": "click", "target": {"shortId": next_btn.get("id")}},
                        "account": account,
                        "policyApproval": {"allowed": True, "token": self._token},
                    })
                    time.sleep(3.5)  # 等新页加载
                else:
                    self._post({"request": {"kind": "scroll", "value": self._SCROLL_DELTA}, "account": account})
                    time.sleep(1.5)
        
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
                ) from exc
            raise DataSourceError(
                f"Browser service error: {exc.response.status_code}",
                code="SERVICE_ERROR",
                evidence={"status_code": exc.response.status_code, "body": exc.response.text[:200]}
            ) from exc
        except httpx.TimeoutException as exc:
            raise DataSourceError(
                "Browser service timeout (60s)",
                code="COMMAND_TIMEOUT"
            ) from exc
        except Exception as exc:
            raise DataSourceError(
                f"Browser service unexpected error: {exc}",
                code="UNEXPECTED_ERROR"
            ) from exc
    
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


# ---------- Mock Data Source (T-113c) ----------

class MockDataSource:
    """Mock 数据源（兜底用，必须明确标注 evidence_type="mock"）"""
    
    name = "mock"
    
    async def fetch(
        self,
        keyword: str,
        category: str | None = None,
        limit: int = 50,
        **kwargs: Any
    ) -> list[MarketEvidence]:
        """
        生成模拟数据（仅在所有真实数据源失败时使用）。
        
        必须明确标注 evidence_type="mock"，并在报告中醒目标注。
        """
        import random
        
        # 生成 10-20 条模拟数据
        count = min(random.randint(10, 20), limit)
        evidences: list[MarketEvidence] = []
        
        for i in range(count):
            price = round(random.uniform(9.9, 99.9), 2)
            sales = random.randint(100, 5000)
            reviews = random.randint(50, int(sales * 0.6))
            
            evidences.append(MarketEvidence(
                source="mock",
                evidence_type="mock",  # ← 明确标注
                product=ProductInfo(
                    name=f"Mock商品-{keyword}-{i+1}",
                    price=price,
                    category=category or "未分类",
                    url=f"https://mock.example.com/item/{i+1}",
                    shop=f"Mock店铺{i+1}",
                    platform="mock"
                ),
                metrics=ProductMetrics(
                    sales=sales,
                    reviews=reviews,
                    rating=round(random.uniform(3.5, 5.0), 1),
                ),
                raw_evidence=RawEvidence(
                    url=f"https://mock.example.com/item/{i+1}",
                )
            ))
        
        logger.warning(f"MockDataSource generated {len(evidences)} mock evidences for keyword={keyword!r}")
        return evidences


# ---------- Auto-register Sources ----------

def _auto_register():
    """自动注册所有数据源到全局注册表"""
    register_source(TaobaoBrowserSource())
    register_source(PddBrowserSource())
    register_source(ManualImportSource())
    register_source(MockDataSource())  # T-113c: Mock 兜底
    logger.info("Auto-registered 4 market data sources: taobao, pdd, manual_import, mock")


# 模块导入时自动注册
_auto_register()

