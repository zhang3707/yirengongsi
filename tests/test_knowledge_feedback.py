def test_knowledge_seed_and_search(client):
    response = client.get("/api/v1/knowledge/search", params={"q": "Pilot"})
    assert response.status_code == 200
    results = response.json()
    assert results, "expected seeded knowledge about Pilot"
    assert all("Pilot" in (item["title"] + item["content"] + " ".join(item["tags"])) for item in results)


def test_knowledge_create_and_list(client):
    created = client.post(
        "/api/v1/knowledge",
        json={
            "title": "测试知识条目",
            "content": "用于验证知识库写入与检索。",
            "tags": ["测试"],
            "source": "pytest",
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/knowledge").json()
    assert any(item["title"] == "测试知识条目" for item in listed)


def test_feedback_priority_is_impact_times_frequency(client):
    high = client.post(
        "/api/v1/feedback",
        json={
            "category": "bug",
            "summary": "任务提交后无响应",
            "impact": "high",
            "frequency": "high",
        },
    )
    assert high.status_code == 201
    assert high.json()["priority"] == "P0"

    low = client.post(
        "/api/v1/feedback",
        json={
            "category": "usability",
            "summary": "按钮间距偏小",
            "impact": "low",
            "frequency": "low",
        },
    )
    assert low.json()["priority"] == "P3"


def test_feedback_categories_are_filterable(client):
    response = client.get("/api/v1/feedback", params={"category": "bug"})
    assert response.status_code == 200
    assert all(item["category"] == "bug" for item in response.json())
