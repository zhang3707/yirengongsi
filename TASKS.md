# TASKS.md — 任务交接与状态机

> **阶段（2026-09-27 起）**：✅ Local MVP 开发收口 → 🚀 **自主运行与问题收集**（让系统自己干活，看它在哪出问题）→ 再决定升级。
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
      验证：pytest 23 通过（新增 6 项），ruff 未跑### 新阶段：自运行 + 问题收集（2026-09-27）

- [x] **T-110 [Phase-Local MVP 关键问题] 控制台无法提交电商发布参数**
      4 字段（product_dir / mode / account / dry_run）已进表单（21c03f2）；
      T-110 已标记完成；policy_approval 仍留 API 层。

- [x] **T-111 [新阶段 · 开放问题池] 让系统自己执行真实业务任务并记录每次问题**
      首个能力落地：T-111 V1 导入数据链 + T-113 V1 Agent 自主采集链
      (`market_research_web`，只读 observe/scroll，严格不编造)。 commit 0bb9f69

- [ ] **T-112 [待真跑] 真实会话跑通第一单 Agent 自主采集**
      owner: 用户 ｜ 前置：EcomAutopilot daemon 会话开启 + 平台登录态
      准备（在 E:\EcomAutopilot\browser-service）：
        node server.mjs（若未在运行）+ session start --account default + 扫码
      验证：API 提交 task_type=market_research + input_payload {platform:taobao, keyword:"PPT模板", pages:3}
      或：AI_COMPANY_LIVE_BROWSER=1 pytest tests/test_market_discovery.py
      owner: <未定> ｜ 状态: pending
      阶段指令: 优先**运行**并**记录**，不新增架构或新功能
      验收: 持续产出的运行结果 + 明确问题清单（AI 质量 / 耗时 / 失败 / 缺料等）
      owner: Codex ｜ 优先级: 关键（阻塞阶段目标 1「本机真实提交真实业务任务」）
      现状:
        - API 端 ecommerce_publish 技能已接入 EcomAutopilot browser-service（HTTP /publish/*）
        - 控制台"任务提交表单"目前仅暴露 title/goal/task_type/priority/user_email
        - input_payload 所需的 product_dir / mode / account / dry_run / policy_approval 全部
          无法在控制台输入；用户只能用 curl / HTTP 客户端手工调 API
      影响: 阻碍 Local MVP 阶段目标 1 —— "本机真实提交真实业务任务（非演示模板）"
      需要: 控制台表单增加4 个输入字段（product_dir 必填，mode/account/dry_run 可选，
          dry_run 默认 True; policy_approval 暂不暴露 UI —— 真实发布仍用 curl/API，先守住安全）
      验收: 用户能在控制台提交一个 DJ-YYYY-XXX 商品目录，五步 workflow 全 succeeded，
          任务详情能看到 build/validate/run 状态树，且 dry_run=true 时永不真跑 browser

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
| 2026-09-27 | 迁移与审计 | 代码同步至 E:\yirengongsi；输出 CODEBASE_STATUS.md（交接文档 §8 要求） |
| 2026-09-27 | 模型层+认证 | shared/model_provider.py + backend/api/auth.py；业务路由 401 保护可测 |
| 2026-09-27 | 阶段收紧 | 定义 Local MVP 阶段 + 冻结清单（多租户/JWT/计费等） |
| 2026-09-27 | T-110 建 issue |
| 2026-09-27 | T-110 完成 | 控制台表单加入 product_dir / mode / account / dry_run 4 字段（policy_approval 留 API 层，守住安全） commit 91c03f2 |
| 2026-09-27 | **Local MVP 收口** |
| 2026-09-27 | **T-113 V1 落地** | Agent 自主采集链 market_research_web（只读+失败语义）；commit 0bb9f69 | 阶段目标 1-4 全部达成；新阶段：让系统自己干活 + 收问题（不开发新功能） | [Phase-Local MVP 关键问题] 控制台无法提交电商发布参数（product_dir/dry_run 等） |
