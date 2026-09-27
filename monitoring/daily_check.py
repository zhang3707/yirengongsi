"""Daily Pilot check: services + AI/Workflow metrics + open issues.

Usage: python monitoring/daily_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from shared.config import settings
from shared.database import SessionLocal
from shared.models import Feedback, LogEntry, Task, WorkflowRun


def main() -> int:
    print(f"== Pilot 每日检查 · environment={settings.environment} ==")
    exit_code = 0

    with SessionLocal() as db:
        try:
            total = db.scalar(select(func.count()).select_from(Task)) or 0
            succeeded = db.scalar(select(func.count()).select_from(Task).where(Task.status == "succeeded")) or 0
            failed = db.scalar(select(func.count()).select_from(Task).where(Task.status == "failed")) or 0
            print("[服务] database=ok")
            print(f"[任务] 总数={total} 成功={succeeded} 失败={failed}")
            if failed:
                exit_code = 1
                print("[告警] 存在失败任务：")
                for task in db.scalars(select(Task).where(Task.status == "failed").limit(10)):
                    print(f"  - {task.id} {task.title} :: {task.error}")
        except Exception as exc:  # noqa: BLE001
            print(f"[服务] database=error: {exc}")
            return 2

        runs = db.scalars(select(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(10)).all()
        print(f"[Workflow] 最近 {len(runs)} 次运行")
        for run in runs:
            print(f"  - {run.workflow} {run.status} step={run.current_step} retries={run.retries}")

        errors = db.scalar(
            select(func.count()).select_from(LogEntry).where(LogEntry.level == "ERROR")
        ) or 0
        print(f"[日志] ERROR 条数={errors}")

        open_feedback = db.scalar(select(func.count()).select_from(Feedback).where(Feedback.status == "open")) or 0
        print(f"[反馈池] open={open_feedback}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
