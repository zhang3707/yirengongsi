def test_builtin_skills_are_registered(client):
    response = client.get("/api/v1/skills/registry")
    assert response.status_code == 200
    names = response.json()
    for expected in ("search", "analysis", "report", "content"):
        assert expected in names


def test_skills_are_synced_to_database(client):
    response = client.get("/api/v1/skills")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"search", "analysis", "report", "content"} <= names


def test_search_skill_returns_sources(client):
    response = client.post(
        "/api/v1/skills/search/test",
        json={"skill": "search", "inputs": {"query": "AI 公司 Pilot", "limit": 3}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["output"]["source_count"] == 3
    assert body["duration_ms"] >= 0


def test_skills_default_research_flow(client):
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"Research Agent", "Analytics Agent", "Content Agent", "Workflow Agent"} <= names
