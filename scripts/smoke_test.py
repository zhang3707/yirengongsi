import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from backend.main import app

with TestClient(app) as client:
    r = client.get("/api/v1/health")
    print("health", r.status_code, r.json()["status"], r.json()["database"])

    r = client.get("/api/v1/agents")
    print("agents", r.status_code, [a["name"] for a in r.json()])

    r = client.get("/api/v1/skills")
    print("skills", r.status_code, [s["name"] for s in r.json()])

    r = client.post("/api/v1/tasks", json={
        "title": "分析本周业务数据并生成报告",
        "goal": "分析本周业务数据，发现异常并给出优化建议",
        "task_type": "analysis",
    })
    print("create task", r.status_code)
    body = r.json()
    if r.status_code >= 400:
        print(body)
    else:
        print("task", body["id"], body["status"], "agent", body["assigned_agent_id"])
        print("runs", [(run["workflow"], run["status"], run["retries"]) for run in body["runs"]])
        for run in body["runs"]:
            print("steps", [(s["name"], s["status"]) for s in run["steps"]])
        print("result head", (body["result"] or "")[:100].replace("\n", " | "))

    r = client.get("/api/v1/metrics/pilot")
    print("metrics", r.status_code, r.json()["technical"])
