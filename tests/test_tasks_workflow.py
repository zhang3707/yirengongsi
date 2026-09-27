def _submit(client, **overrides):
    payload = {
        "title": "分析本周业务数据并生成报告",
        "goal": "分析本周业务数据，发现异常并给出优化建议",
        "task_type": "analysis",
        "auto_run": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/tasks", json=payload)


def test_task_runs_full_workflow(client):
    response = _submit(client)
    assert response.status_code == 201
    body = response.json()

    assert body["status"] == "succeeded"
    assert body["assigned_agent_id"]
    assert body["result"]
    assert body["duration_ms"] is not None

    assert len(body["runs"]) == 1
    run = body["runs"][0]
    assert run["workflow"] == "default"
    assert run["status"] == "succeeded"
    assert [step["name"] for step in run["steps"]] == [
        "task_receive",
        "agent_select",
        "skill_execute",
        "result_generate",
        "save_record",
    ]
    assert all(step["status"] == "succeeded" for step in run["steps"])


def test_workflow_steps_are_persisted(client):
    created = _submit(client, title="持久化检查任务").json()
    detail = client.get(f"/api/v1/tasks/{created['id']}").json()
    steps = detail["runs"][0]["steps"]
    assert all(step["status"] == "succeeded" for step in steps), steps


def test_research_task_uses_search_skill(client):
    created = _submit(
        client,
        title="收集某领域最新信息并生成分析报告",
        task_type="research",
    ).json()
    detail = client.get(f"/api/v1/tasks/{created['id']}").json()
    step = detail["runs"][0]["steps"][2]
    assert "search" in step["detail"]["skills"]


def test_task_evaluation_feeds_metrics(client):
    created = _submit(client, title="评价闭环任务").json()
    response = client.post(
        f"/api/v1/tasks/{created['id']}/evaluation",
        json={
            "quality": 5,
            "minutes_before": 60,
            "minutes_after": 15,
            "experience": 4,
            "trust": 4,
            "reusable": True,
            "comment": "可以直接用于周报初稿",
        },
    )
    assert response.status_code == 201
    assert response.json()["time_saved_ratio"] == 0.75

    metrics = client.get("/api/v1/metrics/pilot").json()
    assert metrics["ai"]["evaluations"] >= 1
    assert metrics["ai"]["average_quality"] > 0


def test_workflow_definitions_are_listed(client):
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    definition = response.json()[0]
    assert definition["name"] == "default"
    assert definition["steps"][0] == "task_receive"


def test_workflow_failure_is_recorded(db_session):
    """A broken agent (skills pointing at a missing skill) must fail loudly and be logged."""
    from shared.models import Agent, Task, WorkflowRun
    from workflow_engine.runner import run_task

    agent = Agent(
        name="Broken Agent",
        domain="broken",
        skills=["does_not_exist"],
        status="active",
    )
    db_session.add(agent)
    db_session.flush()

    task = Task(
        title="必然失败的技能链",
        goal="触发技能不存在",
        task_type="broken",
        assigned_agent_id=agent.id,
    )
    db_session.add(task)
    db_session.flush()
    db_session.commit()

    result = run_task(db_session, task)
    assert result.ok is False
    assert result.failed_step == "skill_execute"

    run = db_session.get(WorkflowRun, result.run.id)
    assert run.status == "failed"
    assert run.retries == 2  # MAX_WORKFLOW_RETRIES default
    failed_step = next(step for step in run.steps if step["name"] == "skill_execute")
    assert failed_step["status"] == "failed"
    assert failed_step["error"]

    refreshed = db_session.get(Task, task.id)
    assert refreshed.status == "failed"
    assert refreshed.error
