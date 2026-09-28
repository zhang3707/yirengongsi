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


- [x] **T-113 V2 风控治理（快失败 + 无重试 + 证据保留）** commit 待填
      owner: Codex ｜ 2026-09-27 22:49 实测：
      任务 `task_9c32331308e2` 在淘宝真实遇风控 → **首轮即显式失败**
      （ANTIBOT_BLOCKED，不进 retry、不伪造数据） —
      工程验证成功：采集器能识别风控并安全停止。
- [~] **T-112 [进行中] 真实会话跑通第一单 Agent 自主采集**
      owner: Codex ｜ 状态: in_progress ｜ since: 2026-09-28

      ### 已打通（今晚验证）
      - Agent 真实浏览器采集链路：淘宝首页 → 搜索框 fill → 搜索钮 click →
        真实商品数据（`s.taobao.com/search` 结果页可见 `人付款` 数据）✅
      - 五步 Workflow 完整 5/5 succeeded（task_dc2143c5ee04，566s）✅
      - 风控治理实测通过：ANTIBOT_BLOCKED 快失败 / COMMAND_TIMEOUT 不重试 ✅
      - 修复真实 bug：
        1) `_merge_step_output` 对 `rows` 的 dict-squash（已改为保留 list）
        2) `wait_for` 与 rounds 冲突（移除，observe 自带 settle_ms）
        3) `COMMAND_TIMEOUT` 加入跳过重试白名单

      ### 下一轮第一件事（明天从这一行开始）
      - [ ] **[阻塞点] 采集 → 分析 → 报告的 findings/sources 传递管道断点**
        现象：`task_dc2143c5ee04` 收到 22 条真实 rows 并 success，
        但最终 `report` 技能收到的 `findings`/`risks`/`sources` 为空 →
        报告内容为"空证据说明"而非真实市场分析。
        定位猜测（一行 diff 即可）：
          `workflow_engine/steps.py::result_generate` 期望的
          findings 来源 key（`analysis.findings`）与 web/analysis 实际
          输出形态（`analysis[0].findings` 等）不对齐；
          或 merge 顺序里 analysis 的 findings 被上游 output 顶掉。
        修法：核对一次 steps.py 的 merge + result_generate 的取值，
        确保：web.rows → analysis.findings → report(findings, sources)。
        验证：重跑一单 pages=2 任务，报告应含真实候选商品、真实价格带。

      ### 备忘（真实环境坑，做了才碰）
      - 淘宝对自动 deny 依赖会话 freshness（manual-search has confirmed
        login state is fine）。「点我反馈」的解封路径保留为人工兜底。
      - operator 短 action id 每页都轮换，**每次 fill/click 前都要重新 observe**
        (`ACTION_ID_NOT_FOUND_NEED_OBSERVE`)。
      - browser-service 对 act 有 45s 硬超时；不要为「礼貌间隔」额外调
        wait_for（observe 的 settle_ms 已经足够）。


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
| 2026-09-28 | T-113a 完成 | Market Evidence Schema + DataSourceRegistry + 3 数据源插件迁移；pytest 43+1；commit 3bc1694 |
| 2026-09-28 | T-112 完成 | findings/sources 传递管道修复；3 项集成测试；pytest 46+1；commit 7bf41f8 |
| 2026-09-28 | T-113c 完成 | Mock 回退机制（默认关闭 + 报告醒目标注）；6 项测试；pytest 52+1 |
| 2026-09-28 | T-113b 完成 | Google Trends RSS + HN Algolia 真实接入（无风控无 key）；6 源注册；5 项真实网络测试；pytest 57+1 |
