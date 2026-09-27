# 《AI公司 MVP v1.0 Pilot部署与运行手册》

版本：v1.0

阶段：真实运行Pilot阶段

适用范围：AI Company MVP v1.0

目标：确保系统稳定部署、运行、监控和反馈闭环

---

# 一、手册定位

本手册用于指导：

```
代码完成

↓

环境部署

↓

系统启动

↓

AI员工配置

↓

任务运行

↓

问题处理

↓

数据反馈
```

---

# 二、MVP运行架构

## 生产运行结构

```

                  User / Operator

                         |

                         ↓

              AI Management Console

                         |

                         ↓

                 API Gateway

                         |

        --------------------------------

        |              |               |

 Agent Runtime   Workflow Engine   Knowledge System

        |              |               |

        --------------------------------

                         |

                  Data Infrastructure

                         |

          PostgreSQL / Redis / Object Storage
```

---

# 三、环境要求

# 1. 基础环境

## Server

最低：

```
CPU:
8 Core

Memory:
32GB

Storage:
200GB SSD
```

---

推荐：

```
CPU:
16 Core

Memory:
64GB

Storage:
500GB SSD
```

---

# 2. 软件环境

必须：

```
Linux

Docker

Docker Compose

PostgreSQL

Redis

Temporal

Nginx
```

---

# 四、项目目录结构

推荐：

```
ai-company-mvp/

├── backend/

│
├── agent-runtime/

│
├── skill-runtime/

│
├── workflow-engine/

│
├── knowledge-service/

│
├── console/

│
├── database/

│
├── docker/

│
├── monitoring/

│
└── docs/
```

---

# 五、部署流程

# Step 1：环境初始化

安装：

- Docker
- Docker Compose
- Git

检查：

```
docker --version

docker compose version
```

---

# Step 2：代码部署

拉取：

```
git clone <repository>
```

进入：

```
cd ai-company-mvp
```

---

# Step 3：配置环境变量

创建：

```
.env
```

包含：

```
DATABASE_URL=

REDIS_URL=

TEMPORAL_HOST=

MODEL_API_KEY=

STORAGE_PATH=

ENVIRONMENT=production
```

---

# Step 4：启动基础服务

启动：

```
docker compose up -d
```

启动：

- PostgreSQL
- Redis
- Temporal
- Backend

---

# Step 5：数据库初始化

执行：

```
migration run
```

检查：

```
users

agents

skills

tasks

workflow_runs

knowledge

logs
```

---

# 六、核心服务启动顺序

必须按照：

```
1.

Database

↓

2.

Redis

↓

3.

Temporal

↓

4.

Backend API

↓

5.

Knowledge Service

↓

6.

Agent Runtime

↓

7.

Workflow Worker

↓

8.

Console
```

---

# 七、Agent初始化流程

进入控制台：

```
AI Console

↓

Agent Management

↓

Create Agent
```

---

配置：

## 基础信息

例如：

```
Name:

Research Agent

Role:

负责信息分析

Description:

负责收集和整理信息
```

---

## 能力配置

绑定：

```
Skills:

- Search Skill

- Analysis Skill

- Report Skill
```

---

## 运行配置

设置：

```
Model:

xxx

Memory:

enabled

Workflow:

default
```

---

# 八、Skill注册流程

进入：

```
Skill Management
```

---

创建Skill：

配置：

```
Skill Name:

Data Analysis

Input:

Dataset

Process:

Analysis

Output:

Report
```

---

测试：

```
Skill Test

↓

Execute

↓

Verify Result
```

---

# 九、Workflow发布流程

进入：

```
Workflow Management
```

---

创建流程：

示例：

```
Task Receive

↓

Agent Select

↓

Skill Execute

↓

Result Generate

↓

Save Record
```

---

发布：

状态：

```
Draft

↓

Testing

↓

Production
```

---

# 十、首次运行测试

## 测试任务

提交：

```
请分析本周业务数据并生成报告
```

---

系统流程：

```
User Request

↓

Task Created

↓

Agent Selected

↓

Workflow Started

↓

Skill Called

↓

Result Returned

↓

Record Saved
```

---

检查：

- 是否完成
- 是否保存记录
- 是否产生日志

---

# 十一、日常运行流程

## 每日启动检查

检查：

### 服务

```
API

Database

Redis

Temporal
```

---

### AI状态

```
Agent在线状态

Workflow状态

异常任务
```

---

### 数据状态

```
任务数量

错误数量

运行时间
```

---

# 十二、监控体系

## 1. 系统监控

指标：

- CPU
- Memory
- Disk
- Network

---

## 2. AI监控

指标：

- Agent调用次数
- 成功率
- 平均耗时
- 用户评价

---

## 3. Workflow监控

指标：

- 执行次数
- 成功率
- 失败节点
- 重试次数

---

# 十三、日志管理

目录：

```
logs/

├── backend/

├── agent/

├── workflow/

├── skill/

└── system/
```

---

日志等级：

## INFO

正常运行。

## WARNING

潜在问题。

## ERROR

需要处理。

---

# 十四、故障处理流程

## P0：系统不可用

处理：

```
发现

↓

停止影响扩大

↓

恢复服务

↓

分析原因

↓

记录事故
```

---

## P1：任务失败

检查：

1. Workflow状态
2. Agent日志
3. Skill日志
4. 输入数据

---

## P2：结果质量问题

处理：

```
记录案例

↓

人工评价

↓

进入反馈池
```

---

# 十五、数据备份

## 数据库

每日：

自动备份。

包括：

- 用户数据
- Agent配置
- Workflow记录
- 知识数据

---

## 文件存储

备份：

- 上传文件
- 输出报告
- 日志

---

# 十六、Pilot运行记录模板

每日记录：

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

---

# 十七、周报模板

每周：

## 运行数据

```
任务：

Agent：

Workflow：

成功率：
```

---

## AI表现

```
优秀案例：

失败案例：

改进建议：
```

---

## 产品反馈

```
用户需求：

体验问题：

优先级：
```

---

# 十八、版本管理规则

当前：

```
AI Company MVP v1.0
```

冻结。

---

修改原则：

## 紧急修复

直接进入：

v1.0.x

---

## 功能优化

进入：

需求池。

---

## 大功能

等待：

下一版本规划。

---

# 十九、Pilot阶段禁止事项

禁止：

❌ 大规模重构

❌ 修改核心架构

❌ 无限增加Agent

❌ 为假设需求开发功能

允许：

✅ 修复Bug

✅ 优化体验

✅ 提升稳定性

✅ 记录需求

---

# 二十、最终运行目标

90天后：

系统达到：

```
稳定运行

+

真实用户使用

+

完整数据记录

+

问题闭环

+

明确下一阶段方向
```

---

# 二十一、当前项目状态

```
AI Company MVP v1.0

开发阶段        ✅完成

闭环验收        ✅完成

部署准备        ✅完成

Pilot运行       ⏳开始

下一阶段：

真实运行数据收集
```

---

下一份进入：

# 《AI公司 MVP v1.0 Pilot首批用户测试方案》

重点：

- 首批用户选择
- 测试任务设计
- 用户反馈采集
- AI效果评价
- Pilot验收标准

项目正式进入真实使用验证。
