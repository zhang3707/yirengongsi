# TASKS.md — 任务交接与状态机

> **当前阶段（2026-09-27 起）**：Local MVP → 本地真实业务闭环验证 → 收集问题 → 再决定升级。
> 冻结：多租户 / JWT / 注册 / 计费 / 分发 / SLA / 商业化认证。详见 AGENTS.md §2。

状态枚举（固定，不得改动）：`pending` | `in_progress` | `done` | `blocked`

图例：`[ ]` pending ・ `[~]` in_progress ・ `[x]` done ・ `[!]` blocked

---

## 当前批次：Pilot 框架搭建（2026-09-27）

### 已完成

- [x] **T-001 读取全部项目文档并提取架构契约**
      owner: Codex ｜ 来源：`一人公司_项目文档.md` + `一人公司_文档拆分/01~03`
      产出：`docs/architecture.md`、`AGENTS.md`

- [x] **T-002 搭建服务骨架（10 个目录）**
      owner: Codex
      产出：`backend/ agent_runtime/ skill_runtime/ workflow_engine/ knowledge_service/`
      `console/ database/ docker/ monitoring/ docs/` + `shared/`

- [x] **T-003 数据模型与迁移**
      owner: Codex
      产出：`shared/models.py`（users/agents/skills/tasks/workflow_runs/knowledge/logs/
      task_evaluations/feedback）、`alembic.ini`、`database/migrations/`、`database/init.sql`

- [x] **T-004 默认 Workflow 五步闭环 + 步骤持久化 + 失败重试**
      owner: Codex
      产出：`workflow_engine/`；步骤状态落库已由测试覆盖

- [x] **T-005 Agent Runtime（注册/选择/技能链）与 Skill Runtime（内置 4 技能）**
      owner: Codex

- [x] **T-006 Knowledge Service 与 Pilot 反馈池（Impact × Frequency → P0-P3）**
      owner: Codex

- [x] **T-007 API Gateway + Console（任务提交 / 记录 / 评价 / 指标）**
      owner: Codex

- [x] **T-008 容器化、监控巡检脚本、文档与测试**
      owner: Codex ｜ 验证：`python -m pytest` → 17 passed；`python scripts/smoke_test.py` 通过；
      `python -m alembic upgrade head` 建表成功；真实 HTTP 服务验证
      （GET /api/v1/health → 200、GET /console/ → 200、POST /api/v1/tasks → 201 且五步全 succeeded）

- [x] **T-009 仓库迁移至 E:\yirengongsi 并输出代码审计报告**
      owner: Codex ｜ 触发：用户反馈在 E 盘看不到代码（原工作目录在 C 盘）
      产出：框架 13 个目录 + 9 个根文件同步至 `E:\yirengongsi`（保留原有 5 份文档）、
      `CODEBASE_STATUS.md`
      验证：E 盘 `python -m pytest` → 17 passed；`alembic upgrade head` 建表成功；
      `scripts/smoke_test.py` 通过（五步 succeeded、成功率 1.0）
- [x] **T-010 模型层（Model Provider）+ 最小认证**
      owner: Codex ｜ 触发：路线 A 第 1-2 步（用户选 A）
      产出：`shared/model_provider.py`（mock / openai-compatible）；4 个技能改为
      模型驱动（mock 模式回落原模板保持测试兼容）；`backend/api/auth.py` 单租户
      Bearer/X-API-Token 保护 7 组业务路由（health/console/docs 公开）
      验证：pytest 23 通过（新增 6 项），ruff 未跑### 待办（Pilot 运行期，按文档优先级）

- [ ] **T-101 真实用户接入与首批任务执行**
      owner: Pilot 管理员 ｜ 目标：5-10 名用户、3-5 个场景、30 天
      验收：`/api/v1/metrics/pilot` 有真实评价数据（评价数 ≥ 10）

- [ ] **T-102 接入真实模型 Provider（替换 mock）**
      owner: 待定 ｜ 依赖：`MODEL_API_KEY` 与供应商确定
      说明：仅替换 provider 实现，不改 Workflow 结构

- [ ] **T-103 Redis / Temporal 启用与 Nginx 反向代理**
      owner: 待定 ｜ 依赖：生产服务器就绪
      验收：`docker compose --profile temporal up -d` 后 worker 正常消费

- [ ] **T-104 首批用户培训材料与反馈问卷**
      owner: 待定 ｜ 依据：`docs/pilot.md`

- [ ] **T-105 V1.1 需求池初始化**
      owner: 待定 ｜ 依赖：T-101 数据积累

---

## 变更记录

| 日期 | 变更 | 说明 |
|---|---|---|
| 2026-09-27 | 初始框架落地 | T-001 ~ T-008 完成，测试全绿 |
| 2026-09-27 | 收尾验证 | 真实 HTTP 端到端验证通过；清理临时数据库文件；README 补充脚本用法 |
| 2026-09-27 | 迁移与审计 |
| 2026-09-27 | 模型层+认证 |
| 2026-09-27 | 阶段收紧 | 定义 Local MVP 阶段 + 冻结清单（多租户/JWT/计费等） | shared/model_provider.py + backend/api/auth.py；业务路由 401 保护可测 | 代码同步至 E:\yirengongsi；输出 CODEBASE_STATUS.md（交接文档 §8 要求） |
