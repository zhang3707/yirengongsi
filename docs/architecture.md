# 运行架构与服务边界

来源：《AI公司 MVP v1.0 Pilot部署与运行手册》第二节。

## 生产运行结构

```
                  User / Operator
                         |
                         v
              AI Management Console        (console/)
                         |
                         v
                 API Gateway                 (backend/)
                         |
        --------------------------------
        |              |               |
 Agent Runtime   Workflow Engine   Knowledge System
 (agent_runtime) (workflow_engine) (knowledge_service)
        |              |               |
        --------------------------------
                         |
                Skill Runtime                (skill_runtime/)
                         |
                  Data Infrastructure
                         |
          PostgreSQL / Redis / Object Storage
```

## 服务职责

| 服务 | 目录 | 职责 | 关键接口 |
|---|---|---|---|
| API Gateway | `backend/` | 路由、鉴权、控制台 API | `/api/v1/*` |
| Agent Runtime | `agent_runtime/` | Agent 注册、选择、技能链解析 | `AgentRegistry` / `AgentSelector` / `AgentRuntime` |
| Skill Runtime | `skill_runtime/` | Skill 注册表、内置技能、执行 | `registry` / `SkillExecutor` |
| Workflow Engine | `workflow_engine/` | 五步流程、步骤持久化、重试 | `WorkflowEngine.run` |
| Knowledge System | `knowledge_service/` | 知识写入、检索、引用 | `KnowledgeService` |
| Console | `console/` | 任务提交、记录查看、评价 | `/console/` |

## 默认 Workflow（文档固定顺序）

```
task_receive  →  agent_select  →  skill_execute  →  result_generate  →  save_record
```

- 每一步写入 `workflow_runs.steps`（含 started_at / finished_at / detail / error）。
- `skill_execute` 失败按 `MAX_WORKFLOW_RETRIES` 重试，仍失败则把任务标记 `failed`。
- 全部成功则任务 `succeeded`，`duration_ms` 落库。

## 任务类型 → 技能链

| task_type | 场景 | 技能链 |
|---|---|---|
| `research` | 信息研究 | search → analysis → report |
| `analysis` | 分析决策 | analysis → report |
| `content` | 内容生产 | content → report |
| `workflow` | 流程管理 | analysis → report |
| `general` | 通用 | analysis → report |

Agent 若显式声明了 skills，则按文档顺序取其声明集合；未注册的技能不会被静默忽略，
而是让 `skill_execute` 失败并被记录（避免"看起来成功、实际降级"）。

## 数据表

`users` · `agents` · `skills` · `tasks` · `workflow_runs` · `knowledge` · `logs`
`task_evaluations` · `feedback`

## 阶段纪律

当前处于 Pilot：禁止大规模重构与架构变更；只做 Bug 修复、体验与稳定性优化，并记录需求。
