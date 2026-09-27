# 项目级协作协议 — 一人公司 / AI Company MVP v1.0

> 本文件是**本项目**的协议唯一来源；全局约定见 `~/.codex/AGENTS.md`。
> 进入项目先读本文件，再动代码。

## 1. 项目定位

- 产品：AI Company MVP v1.0 —— AI 员工工作平台（不是聊天机器人）。
- 当前阶段：**真实运行 Pilot（30-90 天）**。
- 依据文档：`一人公司_项目文档.md`、`一人公司_文档拆分/01~03`；实现映射见 `README.md`。

## 2. 阶段纪律（Pilot 文档硬约束）

**当前阶段（2026-09-27 起）**：

> **Local MVP → 本地真实业务闭环验证 → 收集问题 → 再决定后续升级**

只围绕一件事：**本地单用户完整闭环彻底跑通**。
暂不涉及公网如何部署、别人如何用 —— 这些真实闭环验证完成后另行评估。

### 冻结清单（不得开发，仅作扩展接口预留）

- ❌ 多用户 / Tenant / 多租户
- ❌ JWT
- ❌ 用户注册
- ❌ 计费 / Credits / 额度
- ❌ 公网 SaaS / 分发
- ❌ SLA
- ❌ 商业化认证体系

以上全部**不删除、不忽略**，但**一律不写代码**：
后续真正放量时，只允许通过"追加字段 / 追加路由 / 追加中间件"的方式接进来，
不允许推翻现有模块。

### 阶段目标（未完成即不得进入下一阶段）

1. 本机/内网真实提交真实业务任务（并非演示模板）
2. Agent/Skill/Workflow 全链真实可跑，`task` / `runs` / `logs` / `feedback` 落库完整
3. 真实模型输出可被业务直接采用（或输出可量化失败原因）
4. 问题清单要能沉淀为 `docs/` 或 `TASKS.md` 中可回溯的 issue
5. 达到以上四条才算"闭环完成"，可评估进入下一阶段

### 阶段纪律

允许：修复 Bug、优化体验、提升稳定性、记录需求、401 等微小保障。
禁止：为分布式/公网/多用户/计费/多租户/注册/JWT 等提前铺路。

当前唯一任务：跑通**本地单用户完整真实闭环**并**收集问题**。

## 3. 任务状态机（TASKS.md）

`TASKS.md` 承担任务交接，状态枚举**固定为**：

```
pending | in_progress | done | blocked
```

不得新增、改名或删除状态枚举。`blocked` 条目必须同时包含：

```
blocked_reason: <阻塞原因>
blocked_since: <YYYY-MM-DD>
needs: <需要谁提供什么>
```

## 4. 质量门禁

- 改代码后必须运行相关测试；提交前跑全量：`python -m pytest`。
- 变更不得破坏 `docs/` 中的架构契约（服务边界、Workflow 步骤顺序、状态枚举）。
- 数据库结构变更必须同时提供 Alembic 迁移（`database/migrations/versions/`）。
- 接口变更必须同步更新 `README.md` 的 API 一览。

## 5. 架构契约（不可随意更改）

服务边界与文档一致；目录用下划线（Python 包约束），映射见 `README.md`：

```
backend           API Gateway + Console API + Worker
agent_runtime     Agent 注册、选择、技能链解析
skill_runtime     Skill 注册表与内置技能
workflow_engine   Workflow 定义与五步执行
knowledge_service 知识库写入与检索
console           管理控制台（静态前端）
database          Alembic 迁移与参考 DDL
docker            容器镜像（编排在根 docker-compose.yml）
monitoring        指标定义与每日巡检
docs              架构与运行文档
shared            配置、数据库、模型、Schema、日志
```

固定 Workflow 顺序（不得调整）：

```
task_receive → agent_select → skill_execute → result_generate → save_record
```

## 6. 数据与配置

- 开发默认 SQLite（`data/ai_company.db`），生产用 `DATABASE_URL` 指向 PostgreSQL。
- 不在仓库提交 `.env`、`data/`、`logs/`（已在 `.gitignore`）。
- 模型调用统一走 `MODEL_PROVIDER` 配置；Pilot 默认 `mock`，禁止硬编码密钥。

## 7. 共享记忆

通过 tencent-memory MCP（wiki_* / code_*，只读）读取 Knowledge 库 8421；
写入走本项目 `knowledge_service` 及 `/api/v1/knowledge` 接口，不直接改 MCP 数据。

## 8. 角色分工

- prime-agent：编排器，无人值守闭环。
- Codex：手动干预入口，扮演 Agent 2（架构师 / 验收人）。
