import httpx, json

payload = {
    "title": "考研资料 淘宝真实采集（搜索框 flow）",
    "task_type": "market_research",
    "goal": "Agent 通过淘宝搜索框 flow 真实采集「考研资料」搜索页商品数据（2 页），输出候选项目报告",
    "input_payload": {
        "sources": ["taobao"],
        "keyword": "考研资料",
        "pages": 2,
        "account": "default",
        "allow_mock_fallback": False,
    },
    "auto_run": True,
    "user_email": "pilot@scnet.cn",
}

r = httpx.post("http://127.0.0.1:8000/api/v1/tasks", json=payload, timeout=900)
print("POST:", r.status_code)
t = r.json()
print("task_id:", t.get("id"))
print("status:", t.get("status"), "| error:", (t.get("error") or "")[:200])
print("result_len:", len(t.get("result") or ""))
print("---- result ----")
print((t.get("result") or "")[:2500])
