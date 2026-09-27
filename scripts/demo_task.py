"""端到端演示：创建任务并打印 Workflow 五个步骤的执行结果。

用法：
    python scripts/demo_task.py [任务标题] [task_type]
例：
    python scripts/demo_task.py "收集AI公司Pilot信息" research
    python scripts/demo_task.py "分析本周业务数据并生成报告" analysis
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from shared.database import SessionLocal, init_db
from shared.models import Agent, Task
from workflow_engine.runner import run_task


def ensure_seeded(db) -> bool:
    """Seed demo agents/knowledge when the database is empty."""
    agent_count = db.scalar(select(func.count()).select_from(Agent)) or 0
    if agent_count:
        return False
    from backend.seed import seed_demo_data

    seed_demo_data(db)
    return True


def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "分析本周业务数据并生成报告"
    task_type = sys.argv[2] if len(sys.argv) > 2 else "analysis"

    init_db()
    with SessionLocal() as db:
        if ensure_seeded(db):
            print("(数据库为空，已自动注入演示 Agent / Skill / Knowledge)")

        task = Task(title=title, goal=title, task_type=task_type)
        db.add(task)
        db.flush()
        db.commit()

        result = run_task(db, task)
        agent_name = "-"
        if task.assigned_agent_id:
            agent = db.get(Agent, task.assigned_agent_id)
            agent_name = agent.name if agent else task.assigned_agent_id

        print(f"\n任务 {task.id} · {title} · type={task_type}")
        print(f"Agent: {agent_name}")
        print("Workflow 步骤：")
        for step in result.run.steps:
            print(f"  [{step['status']:>9}] {step['name']}")
        print(f"\n任务状态: {task.status} | 耗时: {task.duration_ms} ms | 重试: {result.run.retries}")
        if task.error:
            print(f"错误: {task.error}")
        print("\n---- 结果 ----")
        print((task.result or "(无结果)")[:600])
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
