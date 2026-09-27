# 首批用户测试方案（Day 1-30）

来源：《AI公司 MVP v1.0 Pilot首批用户测试方案》。

## 目标

验证真实用户 → 真实任务 → AI 员工执行 → 结果交付 → 用户反馈 的闭环。
不是扩大用户数量，重点是找问题、验证价值、收集数据。

## 规模

5-10 名用户、3-5 个真实业务场景、30 天周期。
核心测试用户 5 人 + 观察用户 5 人 + 管理员 1-2 人。

## 四个测试场景与系统能力映射

| 场景 | 用户任务 | 验证能力 | 系统入口 |
|---|---|---|---|
| 信息研究 | 收集信息、整理变化、生成报告 | Research Agent / Knowledge / Report Skill | `task_type=research` |
| 分析决策 | 分析数据、发现异常、给建议 | Analytics Agent / Workflow | `task_type=analysis` |
| 内容生产 | 生成方案/文章/报告/总结 | Content Skill / Knowledge | `task_type=content` |
| 流程管理 | 创建任务、分配 Agent、跟踪、汇总 | Agent 协作 / Workflow Engine | `task_type=workflow` |

## 测试流程

1. **用户初始化**：注册 → 创建工作空间 → 配置权限 → 选择 AI 员工
2. **任务定义**：任务名称 / 目标 / 输入资料 / 期望结果 / 评价标准
3. **AI 执行**：记录 Task ID、Agent、Skill、Workflow、Execution Time、Result
4. **用户评价**：`POST /api/v1/tasks/{id}/evaluation`

## 反馈评分体系（已实现为字段）

| 维度 | 字段 |
|---|---|
| 结果质量 1-5 | `quality` |
| 节省时间 | `minutes_before` / `minutes_after` / `time_saved_ratio` |
| 使用体验 1-5 | `experience` |
| 信任程度 1-5 | `trust` |
| 是否愿意复用 | `reusable` |

## 问题分类与优先级

反馈池类别：`bug` / `usability` / `ai_quality` / `workflow` / `feature_request` / `business_value`。

优先级 = 影响程度 × 发生频率，自动映射 P0-P3（高×高=P0，低×低=P3）。

## 每周访谈问题

1. 哪个功能最有价值？
2. 哪些任务适合交给 AI？
3. 哪些地方不可信？
4. 哪些流程最麻烦？

## 30 天节奏

- Week 1 启动：完成首次任务，关注登录与使用障碍
- Week 2 稳定使用：关注高频任务、常用 Agent/Skill
- Week 3 价值验证：关注时间节省、质量提升
- Week 4 总结：输出《Pilot 30天测试报告》

## 结束输出

1. Pilot 运行报告 2. 用户反馈分析 3. Agent 表现分析 4. Workflow 稳定性报告 5. V1.1 需求池
