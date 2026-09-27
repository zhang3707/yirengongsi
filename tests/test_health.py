def test_health_reports_services(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["services"]["agent_runtime"] == "ok"


def test_root_redirects_to_console(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {307, 308}
    assert response.headers["location"] == "/console/"


def test_console_is_served(client):
    response = client.get("/console/")
    assert response.status_code == 200
    assert "AI Console" in response.text
