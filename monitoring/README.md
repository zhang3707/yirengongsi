# monitoring/

Pilot 监控目录：指标定义、巡检脚本与日志约定。

## 指标来源

| 类别 | 指标 | 获取方式 |
|---|---|---|
| 技术 | 服务可用率、任务成功率、失败数、平均响应时间 | `GET /api/v1/metrics/pilot` |
| AI | 评价数、结果质量、使用体验、信任程度、节省时间比、复用率 | `GET /api/v1/metrics/pilot` |
| Workflow | 执行次数、成功率、失败节点、重试次数 | `GET /api/v1/workflows/runs` |
| 系统 | CPU/内存/磁盘/网络 | 宿主机监控（Prometheus/node_exporter 等） |
| 日志 | 结构化事件 | `logs/<service>/<service>.log` 与 `logs` 表 |

## 巡检脚本

```powershell
python monitoring/daily_check.py
```

输出：服务健康、任务指标、Workflow 失败列表、反馈池摘要，对应运行手册
《十一、日常运行流程》的每日检查。

## 日志目录约定

```
logs/
├── backend/
├── agent/
├── workflow/
├── skill/
└── system/
```
