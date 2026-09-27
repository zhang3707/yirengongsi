# Market Evidence Schema — 多源市场数据统一模型

> **设计目标**：让 `market_research` 技能不再只依赖手动导入，而是支持从多个数据源获取标准化市场数据。
> **核心原则**：采集层和分析层彻底解耦；所有数据源输出统一的 `MarketEvidence` 格式。

## 1. 为什么需要这个层

现状：
- `market_research` 技能只接受手动导入（JSON/CSV）
- `market_research_web` 技能直接从 browser-service 采集，但只支持淘宝/PDD，且容易被风控

问题：
- 淘宝风控严格，真实采集经常失败（ANTIBOT_BLOCKED）
- 没有 fallback 数据源
- 新增数据源需要修改 `market_research_web` 的 handler

解决方案：
- **Market Evidence Schema**：统一数据模型，任何数据源都输出这个格式
- **Data Source Registry**：插件式注册，新数据源只需实现接口
- **多源融合**：`market_research` 可以同时从多个源获取数据并合并

## 2. Market Evidence Schema

```python
{
  "source": "taobao" | "pdd" | "1688" | "google_trends" | "reddit" | "manual_import" | ...,
  "evidence_type": "observed" | "estimated" | "api" | "manual",
  "product": {
    "name": str,
    "price": float,
    "category": str,
    "url": str,
    "image_url": str | None,
    "shop": str | None,
    "platform": str
  },
  "metrics": {
    "sales": int | None,          # 观测到的销量（可能为 None）
    "reviews": int | None,
    "rating": float | None,
    "trend_score": float | None,  # 0-100，来自 Google Trends 等
    "engagement": int | None       # Reddit upvotes / HN points 等
  },
  "collected_at": str,             # ISO 8601 timestamp
  "raw_evidence": {                # 原始证据（用于审计）
    "url": str,
    "page_title": str | None,
    "screenshot_path": str | None,
    "api_response": dict | None,
    "observation_round": int | None
  }
}
```

## 3. 数据源接口

所有数据源实现统一接口：

```python
class DataSource(Protocol):
    name: str
    
    async def fetch(
        self,
        keyword: str,
        category: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> list[MarketEvidence]:
        """获取市场数据，返回标准化的 MarketEvidence 列表"""
        ...
```

## 4. 第一版实现的数据源

### 4.1 已实现（现有代码迁移）

- **TaobaoBrowserSource**（从 `market_research_web` 迁移）
  - 通过 EcomAutopilot browser-service 采集淘宝
  - evidence_type: "observed"
  - 风控治理：ANTIBOT_BLOCKED / LOGIN_REQUIRED / EMPTY_PAGE

- **PddBrowserSource**（从 `market_research_web` 迁移）
  - 同上，PDD 平台

- **ManualImportSource**（从 `market_research` 迁移）
  - 手动导入 JSON/CSV
  - evidence_type: "manual"

### 4.2 计划新增（T-113b）

- **TrendsSource**
  - Google Trends RSS（公开，无风控）
  - evidence_type: "api"
  - 提供 trend_score（0-100）

- **RedditSource**
  - Reddit 公开 JSON API（r/dropship, r/ecommerce 等）
  - evidence_type: "api"
  - 提供 engagement（upvotes）

- **Alibaba1688Source**
  - 1688 开放平台 API（需申请，有免费额度）
  - evidence_type: "api"
  - 提供真实批发价、供应商信息

## 5. 多源融合策略

`market_research` 技能支持同时指定多个数据源：

```json
{
  "sources": ["taobao", "google_trends", "reddit"],
  "keyword": "PPT模板",
  "limit": 50
}
```

融合规则：
1. **去重**：按 `product.url` 去重（同一商品可能被多个源采集到）
2. **合并指标**：同一商品的多个源数据合并（取最新/最全的）
3. **标记来源**：`source` 字段保留所有来源（如 `"taobao+reddit"`）

## 6. 与现有代码的关系

### 6.1 向后兼容

- `market_research` 技能仍然接受手动导入（`products` / `csv` / `json` 参数）
- `market_research_web` 技能保留，但标记为 **deprecated**（推荐用 `market_research` + `sources=["taobao"]`）

### 6.2 数据流

```
用户输入
  ↓
market_research 技能
  ↓
DataSourceRegistry.fetch_all(sources=["taobao", "reddit"])
  ↓
TaobaoBrowserSource.fetch() → list[MarketEvidence]
RedditSource.fetch() → list[MarketEvidence]
  ↓
融合 + 去重
  ↓
统一 rows 格式（兼容现有 market_analysis）
  ↓
market_analysis → opportunity_discovery → project_feasibility
```

## 7. 风控治理原则

所有数据源必须遵守：

1. **快速失败**：检测到风控（ANTIBOT_BLOCKED / LOGIN_REQUIRED）立即停止，不进入重试
2. **有限退避**：普通网络错误可以有限重试（最多 2 次，指数退避）
3. **任务级冷却**：控制每个任务的最大页面数、observe 次数和总运行时间
4. **保留真实失败证据**：URL / 页面状态 / failure code / 最后一次 observation 摘要 / 时间戳
5. **不伪造数据**：采集失败直接返回空列表 + 错误码，不用 mock 数据填充

## 8. 验收标准

- [ ] 新增 `market_evidence.py`，定义 `MarketEvidence` Schema 和 `DataSource` 接口
- [ ] 迁移现有 `market_research_web` 为 `TaobaoBrowserSource` 和 `PddBrowserSource`
- [ ] 迁移现有 `market_research` 的手动导入逻辑为 `ManualImportSource`
- [ ] 实现 `DataSourceRegistry`，支持插件式注册
- [ ] `market_research` 技能支持 `sources` 参数（多源融合）
- [ ] 所有测试通过（pytest 34+）
- [ ] 新增测试覆盖：多源融合、去重、风控治理

## 9. 后续扩展（T-113b）

- [ ] 实现 `TrendsSource`（Google Trends）
- [ ] 实现 `RedditSource`（Reddit 公开 API）
- [ ] 实现 `Alibaba1688Source`（1688 开放平台 API）
- [ ] 支持数据源健康检查（定期探测可用性）
- [ ] 支持数据源优先级（失败时自动切换 fallback）

