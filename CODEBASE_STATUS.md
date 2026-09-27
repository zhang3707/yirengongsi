# CODEBASE_STATUS.md — AI 公司 MVP v1.0 仓库状态审计

> 产出依据：`AI公司_MVP_v1.0_Codex_交接文档.md` 第 8 / 19 节（"先审计，再修改"）。
> 审计日期：2026-09-27 ｜ 审计方式：实际读码 + 实际运行（非静态推断）。
> 结论一句话：**MVP 端到端闭环已打通并可真实运行；未实现项集中在认证授权与真实模型接入。**

---

## 1. 启动方式（已验证）

```powershell
python -m pip install -e ".[dev]"

# 一键：注入演示数据 + 拉起 API + Console
powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1
# 或手动
python -m uvicorn backend.main:app --reload
```

| 入口 | 地址 |
|---|---|
| 控制台 | http://localhost:8000/console/ |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/v1/health |
| Pilot 指标 | http://localhost:8000/api/v1/metrics/pilot |

开发默认 SQLite（`data/ai_company.db`），启动时自动建表 + 注入演示数据；
生产通过 `DATABASE_URL` 指向 PostgreSQL（`AUTO_CREATE_TABLES` / `SEED_DEMO_DATA` 关闭）。

## 2. 当前测试结果（实际运行）

| 命令 | 结果 |
|---|---|
| `python -m pytest` | **17 passed**（2.5s） |
| `python -m alembic upgrade head` | 成功，9 张表 + `alembic_version` |
| `python scripts/demo_task.py "…" research` | 五步全部 `succeeded`，约 47ms |
| `python scripts/smoke_test.py` | health ok / 4 Agents / 4 Skills / 任务 succeeded |
| 真实 HTTP（uvicorn） | `GET /api/v1/health` 200；`GET /console/` 200；`POST /api/v1/tasks` **201** 且五步全绿 |

## 3. 已实现（Implemented）

| 模块 | 状态 | 证据 |
|---|---|---|
| **Data Infrastructure** | 已实现 | `shared/models.py`：User / Agent / Skill / Task / WorkflowRun / Knowledge / LogEntry / TaskEvaluation / Feedback 共 9 表；Alembic `0001` 迁移 |
| **Task 生命周期持久化** | 已实现 | 任务、结果、耗时、错误、时间戳全部落库；无关键状态仅存内存 |
| **Agent Runtime** | 已实现 | `agent_runtime/registry.py`（注册）、`selector.py`（按 domain↔task_type 选择并给出理由）、`runtime.py`（技能链解析）；启动注入 4 个 Agent |
| **Skill Runtime** | 已实现 | `skill_runtime/registry.py` + `executor.py` + 内置 4 技能（search / analysis / report / content）；启动自动同步到 DB |
| **Workflow Engine** | 已实现 | 五步固定顺序 `task_receive → agent_select → skill_execute → result_generate → save_record`；每步状态/起止/详情/错误落库；`skill_execute` 失败按 `MAX_WORKFLOW_RETRIES` 重试 |
| **Knowledge System** | 已实现 | `knowledge_service/service.py`：store / retrieve / inject / 结果沉淀 |
| **API Gateway** | 已实现 | 8 组路由：health / agents / skills / tasks / workflows / knowledge / feedback / metrics |
| **AI Management Console** | 已实现 | `console/`：Dashboard、任务提交与执行链查看、Agent / Skill / Workflow / 知识 / 反馈 / 指标 |
| **反馈池 P0-P3** | 已实现 | 优先级 = Impact × Frequency，测试覆盖 |
| **Observability** | 部分实现 | `logs` 表 + `monitoring/daily_check.py` + `/api/v1/metrics/pilot`；**尚无贯穿全链的 `trace_id`**（日志以 task_id / run_id 关联） |
| **Docker / 部署** | 已实现 | `docker/Dockerfile`、根 `docker-compose.yml`（postgres + redis + api，可选 temporal profile） |

## 4. 与 MVP 架构不一致 / 部分实现（Partial）

| 项 | 现状 | 交接文档期望 | 影响 |
|---|---|---|---|
| **Authentication / Authorization** | **未实现**（无 auth/token/jwt/permission 代码） | 审计项 12；MVP 需认证授权 | Pilot 仅可内网/单机使用；接公网前必须补 |
| **真实模型 Provider** | 使用 `mock-reasoner` 占位 | LLM 调用 | 当前结果是模板化生成，非真实 AI 质量；T-102 |
| **Temporal** | 未接入，用内置 Workflow Engine 顺序执行 | Temporal 作为可靠执行基础设施 | MVP 单机可控；需要分布式/长任务恢复时再启用（T-103） |
| **Redis** | 配置存在但本地未启动 | — | 健康检查显示 `redis: unavailable: TimeoutError`，整体仍 `ok`（由数据库决定） |
| **trace_id** | 无统一 trace_id | 贯穿调用链的 trace_id | 现可经 task → run → steps 追溯；跨服务追踪需补 |

## 5. Stub / TODO / Broken

- **TODO / FIXME / NotImplementedError：代码中 0 处**（全仓库扫描，仅文档内出现示例占位）。
- **Broken：无已知项**；全量测试通过，端到端真实 HTTP 验证通过。
- 唯一"占位"性质的是模型层 `mock-reasoner`（见 §4）。

## 6. 与交接文档 §7 闭环的逐环核对

| 闭环环节 | 状态 |
|---|---|
| User creates Task | PASS |
| Task persisted | PASS |
| Task assigned to Agent | PASS |
| Agent Runtime starts | PASS |
| Agent loads Knowledge | PASS |
| Agent invokes Skill | PASS |
| Skill executes | PASS |
| Workflow coordinates | PASS |
| Result generated | PASS |
| Run / Step / Logs persisted | PASS |
| Console can inspect execution | PASS |
| User receives result | PASS |
| Feedback can be recorded | PASS |

**13/13 环节通过 —— MVP 端到端闭环成立。**

## 7. 最小修复计划（进度更新：2026-09-27 路线 A 开始）

| 优先级 | 事项 | 状态 |
|---|---|---|
| P1 | 接入真实模型 Provider | ✅ 已完成 `shared/model_provider.py`（mock 默认，openai 可选） |
| P1 | 认证授权最小实现 | ✅ 已完成 `backend/api/auth.py`（Bearer / X-API-Token，保护 7 组业务路由） |
| P2 | 统一 `trace_id` 贯穿日志 | 近期做 |
| P2 | 启用 Redis / Temporal + 反向代理 | 依赖生产服务器 |
| P3 | 首批用户培训材料与反馈问卷 | 依赖 T-101 July 序 |

## 7.（原）最小修复计划

| 优先级 | 事项 | 类型 | 依赖 |
|---|---|---|---|
| P1 | 接入真实模型 Provider（替换 mock，仅换 provider 实现，不动 Workflow 结构） | 补缺口 | `MODEL_API_KEY` + 供应商确定 |
| P1 | 认证授权最小实现（单租户 Token + 路由保护） | 补缺口 | 无（可立即做） |
| P2 | 统一 `trace_id` 贯穿日志 | 可观测性 | 无 |
| P2 | 启用 Redis / Temporal + 反向代理 | 基础设施 | 生产服务器就绪 |
| P3 | 首批用户培训材料与反馈问卷 | 运营 | 依据 `docs/pilot.md` |

> 纪律：以上均属"补齐已确定 MVP"，**不新增大功能、不重构已实现模块**。
> 后续能力一律由真实运行数据与实际问题驱动（交接文档 §14 / §21）。

## 8. 风险

| 风险 | 说明 |
|---|---|
| 无认证即对外暴露 | 当前仅适合内网/单机 Pilot；公网部署前必须完成认证 |
| mock 模型 ≠ 真实 AI 质量 | Pilot 的"AI 质量"指标在接入真实模型前不具参考性 |
| 进程内执行、无外部队列 | 长任务或崩溃恢复依赖 Temporal（当前未启用） |
| Redis 不可用时健康检查仍 ok | 部署时需人工确认 Redis 状态字段，勿只看 `status` |

## 9. 结论

现有代码**不是空仓库，也不是需要重写的原型**：9 张表、五步 Workflow、4 个 Agent、4 个
Skill、控制台与真实 HTTP 闭环均已可运行，17 项测试通过。

因此按交接文档原则 1（不要推翻重写）执行：
**优先修复 → 局部重构 → 替换单模块 → 最后才考虑重写**。
下一步动作 = §7 的 P1 两项，而非设计 V1.5 / V2。
