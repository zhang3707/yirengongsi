# 部署与运行手册

来源：《AI公司 MVP v1.0 Pilot部署与运行手册》。

## 1. 环境要求

最低：8 Core / 32GB / 200GB SSD。推荐：16 Core / 64GB / 500GB SSD。

软件：Linux、Docker、Docker Compose、PostgreSQL、Redis、Temporal（可选）、Nginx。

## 2. 本地开发启动

```powershell
python -m pip install -e ".[dev]"
python -m uvicorn backend.main:app --reload
```

默认 SQLite（`data/ai_company.db`），自动建表并注入演示数据。

## 3. 容器化部署

```powershell
Copy-Item .env.example .env
docker compose up -d                  # postgres + redis + api
docker compose --profile temporal up -d   # 可选：Temporal + workflow worker
```

## 4. 环境变量

见 `.env.example`：`DATABASE_URL` / `REDIS_URL` / `TEMPORAL_HOST` / `MODEL_API_KEY`
/ `STORAGE_PATH` / `ENVIRONMENT`。

`DATABASE_URL` 为空时自动回落到本地 SQLite；生产必须显式配置 PostgreSQL。

## 5. 数据库初始化

```powershell
alembic upgrade head     # 推荐（迁移管理）
```

或让应用启动时自动建表（`AUTO_CREATE_TABLES=true`）。
运行手册要求确认的表：`users / agents / skills / tasks / workflow_runs / knowledge / logs`。

## 6. 服务启动顺序（必须遵守）

```
1 Database → 2 Redis → 3 Temporal → 4 Backend API
→ 5 Knowledge Service → 6 Agent Runtime → 7 Workflow Worker → 8 Console
```

其中 5–8 由 API 进程内的 lifespan 按序初始化（skill → db → seed），
独立部署时可另起 `python -m backend.worker`。

## 7. Agent 配置流程

Console → Agent Management，或：

```powershell
curl -X POST http://localhost:8000/api/v1/agents -H "Content-Type: application/json" -d @agent.json
```

配置基础信息（name/role/description）、能力（skills 绑定）、运行配置（model/memory/workflow）。

## 8. Skill 注册流程

内置技能在启动时自动注册并同步到 `skills` 表。自建技能：

1. 在 `skill_runtime/builtin/` 新增 `SkillDefinition`；
2. 加入 `BUILTIN_SKILLS`；
3. 重启后自动同步；
4. 用 `POST /api/v1/skills/{name}/test` 验证。

## 9. Workflow 发布流程

默认流程名称 `default`，状态语义：Draft → Testing → Production。
当前 Pilot 使用 Production 默认流程；新增流程请在 `workflow_engine/definitions.py` 注册。

## 10. 首次运行测试

```powershell
python scripts/smoke_test.py
```

预期：health ok、4 个 Agent、4 个 Skill、任务 `succeeded`、五个步骤全部 `succeeded`。

## 11. 版本管理

MVP v1.0 冻结：紧急修复进入 `v1.0.x`，功能优化进入需求池，大功能等待下一版本。
