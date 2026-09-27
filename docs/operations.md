# 日常运维、监控与故障处理

来源：《AI公司 MVP v1.0 Pilot部署与运行手册》第十一至十七节。

## 每日启动检查

```powershell
python monitoring/daily_check.py
```

检查项：
- 服务：API / Database / Redis / Temporal
- AI 状态：Agent 在线状态、Workflow 状态、异常任务
- 数据状态：任务数量、错误数量、运行时间

## 监控指标

| 类别 | 指标 | 获取方式 |
|---|---|---|
| 系统 | CPU / Memory / Disk / Network | 宿主机监控 |
| AI | Agent 调用次数、成功率、平均耗时、用户评价 | `/api/v1/metrics/pilot` |
| Workflow | 执行次数、成功率、失败节点、重试次数 | `/api/v1/workflows/runs` |

## 日志

```
logs/
├── backend/
├── agent/
├── workflow/
├── skill/
└── system/
```

等级：INFO 正常 / WARNING 潜在问题 / ERROR 需要处理。

结构化事件同时写入 `logs` 表（`GET /api/v1/metrics/activity` 可看最近任务）。

## 故障处理流程

- **P0 系统不可用**：发现 → 停止影响扩大 → 恢复服务 → 分析原因 → 记录事故
- **P1 任务失败**：依次检查 ① Workflow 状态 ② Agent 日志 ③ Skill 日志 ④ 输入数据
- **P2 结果质量问题**：记录案例 → 人工评价 → 进入反馈池

失败任务排查：

```powershell
curl "http://localhost:8000/api/v1/tasks?status=failed"
curl "http://localhost:8000/api/v1/workflows/runs?status=failed"
```

重跑：`POST /api/v1/workflows/runs/{run_id}/retry`。

## 数据备份

每日备份数据库（用户数据 / Agent 配置 / Workflow 记录 / 知识数据）与文件存储
（上传文件 / 输出报告 / 日志）。

## 每日运行记录模板

```
日期：
系统状态：
任务数量：
成功数量：
失败数量：
主要问题：
用户反馈：
需要优化：
```

## 周报模板

```
运行数据：任务 / Agent / Workflow / 成功率
AI 表现：优秀案例 / 失败案例 / 改进建议
产品反馈：用户需求 / 体验问题 / 优先级
```

## Pilot 期间禁止事项

禁止：大规模重构、修改核心架构、无限增加 Agent、为假设需求开发功能。
允许：修复 Bug、优化体验、提升稳定性、记录需求。
