# 一人公司 · AI Company MVP v1.0

AI 员工工作平台的最小可运行框架（Pilot 阶段），依据三份文档搭建：
《真实运行 Pilot 计划（30-90 天）》《Pilot 部署与运行手册》《Pilot 首批用户测试方案》。

> **不是聊天机器人。** 用户提交**任务** → 系统选择 **Agent** → 调用 **Skill** →
> **Workflow** 编排 → 交付结果并记录全过程。

## 快速开始

```powershell
python -m pip install -e ".[dev]"

# 一键启动（先注入演示数据，再拉起 API + Console）
powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1

# 或手动启动
python -m uvicorn backend.main:app --reload
```

| 入口 | 地址 |
|---|---|
| 控制台 | http://localhost:8000/console/ |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/v1/health |
| Pilot 指标 | http://localhost:8000/api/v1/metrics/pilot |

开发环境默认使用 SQLite（`data/ai_company.db`），自动建表并注入 4 个 Agent 与 3 条知识。
生产环境通过 `DATABASE_URL` 指向 PostgreSQL。

## 容器化部署

```powershell
Copy-Item .env.example .env
docker compose up -d                       # postgres + redis + api
docker compose --profile temporal up -d    # 可选：Temporal + workflow worker
```

## 目录结构

| 文档中的名称 | 本仓库目录 | 说明 |
|---|---|---|
| `backend/` | `backend/` | API Gateway、路由、Worker |
| `agent-runtime/` | `agent_runtime/` | Agent 注册、选择、技能链解析 |
| `skill-runtime/` | `skill_runtime/` | Skill 注册表与内置技能 |
| `workflow-engine/` | `workflow_engine/` | 五步流程、步骤持久化、重试 |
| `knowledge-service/` | `knowledge_service/` | 知识写入、检索、引用 |
| `console/` | `console/` | 管理控制台（原生 HTML/CSS/JS） |
| `database/` | `database/` | Alembic 迁移与参考 DDL |
| `docker/` | `docker/` | 镜像定义（编排文件在根 `docker-compose.yml`） |
| `monitoring/` | `monitoring/` | 指标定义与每日巡检脚本 |
| `docs/` | `docs/` | 架构、部署、运维、Pilot 文档 |

目录使用下划线是 Python 包命名约束；与文档中的连字符名称一一对应。

## 核心能力

### 默认 Workflow（文档固定顺序）

```
task_receive → agent_select → skill_execute → result_generate → save_record
```

每一步都写入 `workflow_runs.steps`（状态、起止时间、详情、错误）。
`skill_execute` 失败按 `MAX_WORKFLOW_RETRIES` 重试，仍失败则任务标记 `failed` 并记录日志。

### 任务类型 → 技能链

| task_type | 场景 | 技能链 |
|---|---|---|
| `research` | 信息研究 | search → analysis → report |
| `analysis` | 分析决策 | analysis → report |
| `content` | 内容生产 | content → report |
| `workflow` | 流程管理 | analysis → report |

### 应用层配置（Model Provider / 认证）

在项目根 `.env`（参考 `.env.example`）中：

| 变量 | 作用 |
|---|---|
| `MODEL_PROVIDER` | `mock`（默认，确定性模板） 或 `openai`（任何 OpenAI 兼容接口：OpenAI / DeepSeek / Moonshot / Qwen…） |
| `MODEL_BASE_URL` | 非 mock 必填，如 `https://api.deepseek.com/v1` |
| `MODEL_API_KEY` | 非 mock 必填 |
| `MODEL_NAME` | 模型名，如 `gpt-4o-mini` / `deepseek-chat` |
| `API_AUTH_TOKEN` | 留空 = 不启用认证；填了即可保护全部业务路由 |
| `API_AUTH_ENABLED` | 额外开关，默认 `false` |
| `API_TIMEOUT_SECONDS` | 模型超时（秒），默认 120 |

`/api/v1/health`、`/console/`、`/docs` 永远公开；业务路由需要 Token 时用
`Authorization: Bearer <token>` 或 `X-API-Token: <token>`。

### API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 服务 / 数据库 / Redis 状态 |
| GET/POST | `/api/v1/agents` | Agent 列表 / 创建 |
| GET/POST | `/api/v1/skills` | Skill 列表 / 注册 |
| POST | `/api/v1/skills/{name}/test` | 技能试跑 |
| GET/POST | `/api/v1/tasks` | 任务列表 / 提交并运行 |
| GET | `/api/v1/tasks/{id}` | 任务详情（含 Workflow 步骤与结果） |
| POST | `/api/v1/tasks/{id}/run` | 重跑任务 |
| POST | `/api/v1/tasks/{id}/evaluation` | Pilot 用户评价（质量/省时/体验/信任） |
| GET | `/api/v1/workflows` | Workflow 定义 |
| GET | `/api/v1/workflows/runs` | 运行记录 |
| POST | `/api/v1/workflows/runs/{id}/retry` | 重试运行 |
| GET/POST | `/api/v1/knowledge` | 知识列表 / 写入 |
| GET | `/api/v1/knowledge/search?q=` | 知识检索 |
| GET/POST | `/api/v1/feedback` | 反馈池 / 提交（自动算 P0-P3） |
| GET | `/api/v1/metrics/pilot` | 技术 / AI / 反馈指标 |

## 数据库迁移

```powershell
alembic upgrade head
alembic revision --autogenerate -m "描述"
```

## 测试与自检

```powershell
python -m pytest                    # 全量测试（17 项）
python scripts/smoke_test.py        # 端到端冒烟（health + Agents + Skills + 任务）
python scripts/demo_task.py "收集AI公司Pilot运行信息" research   # 单任务五步演示
python scripts/seed.py              # 建表 + 注入演示 Agent / Skill / 知识
python monitoring/daily_check.py    # Pilot 每日巡检
```

## 文档索引

- [`docs/architecture.md`](docs/architecture.md) — 运行架构与服务边界
- [`docs/deployment.md`](docs/deployment.md) — 部署、启动顺序与配置流程
- [`docs/operations.md`](docs/operations.md) — 日常运维、监控、故障处理
- [`docs/pilot.md`](docs/pilot.md) — 首批用户测试方案与反馈闭环
- [`TASKS.md`](TASKS.md) — 任务状态机与待办
- [`AGENTS.md`](AGENTS.md) — 项目协作协议（唯一来源）

## 阶段纪律

MVP v1.0 已冻结：只允许修复 Bug、优化体验、提升稳定性、记录需求。
禁止大规模重构、改核心架构、无限增加 Agent、为假设需求开发功能。
