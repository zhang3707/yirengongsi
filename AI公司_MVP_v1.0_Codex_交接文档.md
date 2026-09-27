# AI公司 MVP v1.0 --- Codex 开发交接文档

> 文档用途：将当前"AI公司 / 一人公司"项目的最终 MVP 状态交接给
> Codex，作为后续代码开发、调试、部署和问题修复的统一上下文。
>
> 重要原则：**当前阶段不是继续做架构升级，而是把已经确定的 MVP
> 真正落地、跑通、稳定运行。后续改造必须由真实运行数据、用户反馈或实际开发中暴露的问题驱动。**

------------------------------------------------------------------------

## 1. 项目定位

项目目标不是继续围绕淘宝做一个垂直工具，而是建设一个通用的：

**AI Company Operating System / AI 公司运行系统**

核心思想：

``` text
业务任务
  ↓
AI Management Console
  ↓
AI Organization
  ↓
Agent Runtime
  ↓
Skill Runtime
  ↓
Workflow Engine / Temporal
  ↓
Knowledge System
  ↓
Data Infrastructure
  ↓
结果 / 日志 / 指标 / 反馈
  ↓
下一轮任务执行
```

淘宝只是此前用于验证系统闭环的业务场景。

**淘宝阶段已经收口，不再继续增加淘宝商品测试，也不再以淘宝专项开发作为当前主线。**

------------------------------------------------------------------------

# 2. 当前阶段结论

当前项目进入：

## MVP v1.0 最终落地阶段

目标只有三个：

1.  把现有 MVP 代码完整落地；
2.  打通端到端真实运行闭环；
3.  进入真实 Pilot，依据实际数据继续迭代。

当前不做：

-   无依据的架构扩张
-   无限增加测试商品
-   为未来场景提前设计复杂系统
-   自主进化 AI
-   完全自主 AI 公司
-   大规模多租户商业化
-   过早的微服务化
-   为"可能出现的问题"提前堆功能

------------------------------------------------------------------------

# 3. MVP 已确定的核心模块

## 3.1 Data Infrastructure

负责：

-   用户 / 租户基础数据
-   业务数据
-   Agent 数据
-   Skill 数据
-   Workflow 数据
-   Task / Run / Execution 数据
-   日志
-   指标
-   反馈
-   状态持久化

要求：

-   数据模型清晰
-   状态可追踪
-   执行记录可查询
-   不允许关键状态只存在内存

------------------------------------------------------------------------

## 3.2 Knowledge System

职责：

-   业务知识
-   Agent 上下文
-   Skill 文档
-   SOP
-   历史执行结果
-   用户反馈
-   可复用经验

MVP 阶段重点不是做复杂"自主知识进化"，而是保证：

``` text
知识可存
知识可取
知识可注入 Agent
执行结果可沉淀
```

------------------------------------------------------------------------

## 3.3 Skill Runtime

Skill 是 Agent 可以调用的能力单元。

典型结构：

``` text
Skill
├── metadata
├── input schema
├── output schema
├── executor
├── permission
├── timeout
├── retry policy
└── logging
```

Skill Runtime 需要解决：

-   Skill 注册
-   Skill 查询
-   参数校验
-   执行
-   超时
-   错误处理
-   执行日志
-   结果返回

原则：

**Skill 是可组合能力，不应该把大量业务逻辑硬编码进 Agent。**

------------------------------------------------------------------------

# 4. Agent Runtime

Agent Runtime 是 MVP 的核心执行层。

基本生命周期：

``` text
Task
 ↓
Agent
 ↓
Load Context
 ↓
Load Knowledge
 ↓
Select / Call Skill
 ↓
Execute
 ↓
Observe Result
 ↓
Continue / Finish
 ↓
Persist Run
```

必须具备：

-   Agent 配置
-   Agent 状态
-   Task 输入
-   Context
-   Tool / Skill 调用
-   LLM 调用
-   Execution trace
-   Error handling
-   Result persistence

MVP 阶段优先保证**确定性、可观察性、可调试性**，不要优先追求完全自主。

------------------------------------------------------------------------

# 5. Workflow Engine / Temporal

Workflow 用于编排多步骤业务任务。

基本模型：

``` text
Workflow
 ├── Trigger
 ├── Step
 ├── Agent
 ├── Skill
 ├── Condition
 ├── Retry
 ├── Timeout
 └── Completion
```

需要保证：

-   Workflow 可启动
-   Workflow 状态可追踪
-   Step 状态可追踪
-   失败可重试
-   超时可处理
-   中断后可以恢复
-   执行结果持久化

Temporal 是工作流可靠执行基础设施。

不要在 MVP 阶段自行重复实现 Temporal 已经解决的问题。

------------------------------------------------------------------------

# 6. AI Management Console

前端控制台不是普通后台，而是 AI 公司运行入口。

MVP 至少需要能够观察：

### Dashboard

-   系统状态
-   Agent 数量
-   Skill 数量
-   Workflow 数量
-   Task / Run
-   成功 / 失败
-   最近执行

### Agent

-   Agent 列表
-   Agent 配置
-   Agent 状态
-   Agent 执行记录

### Skill

-   Skill 列表
-   Skill 配置
-   Skill 执行
-   Skill 错误

### Workflow

-   Workflow 列表
-   Workflow 状态
-   Workflow Run
-   Step 执行状态

### Logs / Runs

必须能回答：

> "这个任务到底发生了什么？"

因此日志和执行链是 MVP 的核心，不是附属功能。

------------------------------------------------------------------------

# 7. MVP 端到端闭环

Codex 开发完成后，至少必须验证下面这条链：

``` text
User creates Task
        ↓
Task persisted
        ↓
Task assigned to Agent
        ↓
Agent Runtime starts
        ↓
Agent loads Knowledge
        ↓
Agent invokes Skill
        ↓
Skill executes
        ↓
Workflow coordinates if required
        ↓
Result generated
        ↓
Run / Step / Logs persisted
        ↓
Console can inspect execution
        ↓
User receives result
        ↓
Feedback can be recorded
```

任何一环断开，都不能认为 MVP 真正闭环。

------------------------------------------------------------------------

# 8. Codex 第一优先级

Codex 接手后，不要直接设计 V1.5 / V2。

第一步：

## 检查现有代码仓库

重点检查：

``` text
1. Repository structure
2. README
3. package / dependency management
4. backend
5. frontend
6. database
7. migrations
8. Agent Runtime
9. Skill Runtime
10. Workflow / Temporal
11. Knowledge
12. authentication / authorization
13. configuration
14. environment variables
15. tests
16. Docker / deployment
17. observability
```

然后输出：

``` text
CODEBASE_STATUS.md
```

内容至少包含：

-   已实现
-   部分实现
-   Stub
-   TODO
-   Broken
-   Missing
-   与 MVP 架构不一致的地方
-   启动方法
-   当前测试结果

**先审计，再修改。**

------------------------------------------------------------------------

# 9. Codex 开发原则

## 原则 1：不要推翻重写

除非现有实现已经明确阻碍 MVP，否则：

``` text
优先修复
>
局部重构
>
替换单模块
>
最后才考虑重写
```

------------------------------------------------------------------------

## 原则 2：不要为了架构漂亮增加复杂度

优先：

``` text
可运行
可测试
可观察
可维护
```

而不是：

``` text
复杂
分布式
高度抽象
过度通用
```

------------------------------------------------------------------------

## 原则 3：所有执行必须可追踪

任何：

-   Agent Run
-   Skill Run
-   Workflow Run
-   Task

都应该有唯一 ID，并能够关联：

``` text
Task
 ↓
Workflow Run
 ↓
Agent Run
 ↓
Skill Run
 ↓
Result
 ↓
Logs
```

------------------------------------------------------------------------

## 原则 4：失败必须可定位

出现错误时至少能够回答：

-   哪个 Task？
-   哪个 Workflow？
-   哪个 Agent？
-   哪个 Skill？
-   哪一步？
-   输入是什么？
-   错误是什么？
-   重试过几次？
-   最终状态是什么？

------------------------------------------------------------------------

## 原则 5：配置与代码分离

以下内容尽量配置化：

-   Agent prompt
-   Skill metadata
-   Workflow definition
-   Model
-   Timeout
-   Retry
-   Permission
-   Knowledge source

------------------------------------------------------------------------

# 10. 推荐开发顺序

## Phase 0 --- Codebase Audit

先完成：

``` text
CODEBASE_STATUS.md
```

并确认：

``` text
可以启动
可以构建
可以测试
可以访问数据库
```

------------------------------------------------------------------------

## Phase 1 --- Backend Foundation

确认：

-   Database
-   Migration
-   Models
-   Repository / Service
-   API
-   Authentication
-   Error handling

------------------------------------------------------------------------

## Phase 2 --- Agent Runtime

完成：

``` text
Task
→ Agent
→ Context
→ LLM
→ Skill
→ Result
→ Run persistence
```

------------------------------------------------------------------------

## Phase 3 --- Skill Runtime

完成：

``` text
register
→ discover
→ validate
→ execute
→ result
→ log
```

------------------------------------------------------------------------

## Phase 4 --- Workflow

完成：

``` text
Workflow
→ Step
→ Agent / Skill
→ Retry
→ Timeout
→ Completion
```

------------------------------------------------------------------------

## Phase 5 --- Knowledge

完成：

``` text
store
→ retrieve
→ inject
→ persist result
```

------------------------------------------------------------------------

## Phase 6 --- Console

完成：

``` text
Dashboard
Agent
Skill
Workflow
Task
Run
Logs
```

------------------------------------------------------------------------

## Phase 7 --- E2E

至少跑通：

### Case A：简单 Agent Task

``` text
User
→ Task
→ Agent
→ Result
```

### Case B：Agent + Skill

``` text
User
→ Task
→ Agent
→ Skill
→ Result
```

### Case C：Workflow

``` text
User
→ Workflow
→ Step 1
→ Step 2
→ Agent
→ Skill
→ Result
```

### Case D：失败恢复

``` text
Task
→ Skill failure
→ Retry
→ Success
```

------------------------------------------------------------------------

# 11. 测试要求

MVP 不需要无限扩大业务数据规模。

测试重点从：

``` text
“测试多少商品”
```

转为：

``` text
“系统闭环是否可靠”
```

核心测试：

### Unit Test

-   Agent
-   Skill
-   Workflow
-   Repository
-   API

### Integration Test

-   DB
-   Agent + Skill
-   Workflow + Agent
-   Workflow + Temporal

### E2E Test

完整用户任务闭环。

### Failure Test

至少覆盖：

-   LLM failure
-   Skill failure
-   timeout
-   workflow failure
-   invalid input
-   permission denied
-   dependency unavailable

------------------------------------------------------------------------

# 12. Observability

MVP 必须能够观察：

``` text
Task count
Run count
Success rate
Failure rate
Retry count
Latency
Token / model usage（如可获取）
Skill execution
Workflow execution
Agent execution
```

日志至少包含：

``` text
timestamp
trace_id
task_id
workflow_id
agent_id
skill_id
status
duration
error
```

推荐统一：

``` text
trace_id
```

贯穿整个调用链。

------------------------------------------------------------------------

# 13. 数据模型的核心关系

逻辑关系建议保持：

``` text
User
 │
 └── Task
       │
       └── WorkflowRun
              │
              ├── WorkflowStepRun
              │      ├── AgentRun
              │      └── SkillRun
              │
              └── Result
```

另外：

``` text
Agent
 ├── Knowledge
 ├── Skills
 └── Configuration

Workflow
 ├── Agents
 ├── Skills
 └── Steps
```

具体表结构以现有代码为准。

**不要在没有检查现有 schema 前重新设计数据库。**

------------------------------------------------------------------------

# 14. 当前冻结范围

以下内容暂时冻结：

## 不做

-   淘宝专项继续开发
-   无限商品测试
-   自主 AI 公司
-   Agent 自主创建 Agent
-   自动组织重构
-   自主能力进化
-   大规模商业化
-   多租户复杂计费
-   复杂插件市场
-   过度复杂的权限系统
-   过度复杂的知识图谱
-   大规模分布式改造
-   为未来场景提前实现大量接口

## 什么时候可以做？

只有出现：

``` text
真实用户需求
或
真实运行问题
或
明确性能瓶颈
或
明确商业需求
```

才进入需求池。

------------------------------------------------------------------------

# 15. 产品迭代原则

以后每次升级都应该遵循：

``` text
真实运行
 ↓
数据
 ↓
问题
 ↓
反馈
 ↓
需求
 ↓
设计
 ↓
开发
 ↓
测试
 ↓
发布
 ↓
再次运行
```

而不是：

``` text
想象未来
 ↓
提前设计
 ↓
提前开发
 ↓
增加复杂度
```

------------------------------------------------------------------------

# 16. Pilot 阶段

MVP 完成后进入真实 Pilot。

目标：

-   找真实问题
-   找真实用户价值
-   找真实稳定性问题
-   找 AI 质量问题
-   找 Workflow 问题
-   找 UX 问题

反馈分类：

``` text
P0 — 系统不可用
P1 — 核心业务无法完成
P2 — 明显影响效率
P3 — 普通体验问题
P4 — Future Request
```

Feature Request 不因为"看起来有价值"就直接开发。

先观察：

``` text
frequency
impact
business value
implementation cost
```

------------------------------------------------------------------------

# 17. Codex 每次开发完成后的交付格式

每个开发任务结束后，输出：

``` text
## Change

做了什么

## Reason

为什么做

## Files

修改了哪些文件

## Database

是否修改 DB / Migration

## API

是否修改 API

## Runtime

是否影响 Agent / Skill / Workflow

## Tests

运行了哪些测试

## Result

测试结果

## Risks

已知风险

## Next

下一步
```

------------------------------------------------------------------------

# 18. Git 提交原则

建议：

``` text
feat:
fix:
refactor:
test:
docs:
chore:
```

每个 commit 尽量保持单一目的。

例如：

``` text
feat(agent): implement agent task execution
feat(skill): add skill runtime execution
fix(workflow): handle retry state persistence
test(e2e): add agent skill workflow test
docs: add codex handoff
```

不要把大量无关修改塞进一个 commit。

------------------------------------------------------------------------

# 19. Codex 的第一条任务

接手后第一条任务不是开发新功能。

请执行：

``` text
1. Inspect repository
2. Read README
3. Read architecture / docs
4. Inspect backend
5. Inspect frontend
6. Inspect database
7. Inspect Agent Runtime
8. Inspect Skill Runtime
9. Inspect Workflow / Temporal
10. Inspect tests
11. Run the project
12. Run existing tests
13. Identify blockers
14. Create CODEBASE_STATUS.md
```

然后根据：

``` text
CODEBASE_STATUS.md
+
本交接文档
```

制定**最小修复计划**。

------------------------------------------------------------------------

# 20. 完成标准

只有同时满足下面条件，才认为 MVP 真正完成：

### Build

``` text
Backend build PASS
Frontend build PASS
```

### Runtime

``` text
Backend starts PASS
Frontend starts PASS
Database connects PASS
Temporal / Workflow infrastructure PASS
```

### Agent

``` text
Task → Agent → Result PASS
```

### Skill

``` text
Agent → Skill → Result PASS
```

### Workflow

``` text
Workflow → Step → Agent / Skill → Result PASS
```

### Persistence

``` text
Task persisted PASS
Run persisted PASS
Result persisted PASS
Logs persisted PASS
```

### Failure

``` text
Failure → Retry / Error → Final State PASS
```

### Console

``` text
Can inspect Task
Can inspect Agent
Can inspect Skill
Can inspect Workflow
Can inspect Run
Can inspect Logs
```

### E2E

``` text
User
→ Task
→ Agent
→ Skill
→ Workflow
→ Result
→ Persistence
→ Console
```

完整闭环 PASS。

------------------------------------------------------------------------

# 21. 最终交接结论

当前项目不再处于：

> "继续设计一个越来越大的 AI 系统"

而处于：

> **"把已经确定的 AI 公司 MVP 做成真正可以运行的软件。"**

Codex 的职责：

``` text
理解现有代码
 ↓
验证当前状态
 ↓
补齐 MVP 缺口
 ↓
打通 E2E
 ↓
修复真实问题
 ↓
稳定运行
```

而不是：

``` text
重新设计整个系统
```

**如果现有代码已经实现某项能力，不要为了"更漂亮"而重写。**

**如果没有真实问题，不要主动升级架构。**

**如果发现问题，优先最小改动解决，并留下测试。**

------------------------------------------------------------------------

## 22. 交接给 Codex 的一句话

> **先把现有 AI 公司 MVP 跑起来、跑通、跑稳定；不要扩张需求，不要提前做
> V2。所有下一阶段能力，都等真实运行数据和实际问题出现后再决定。**
