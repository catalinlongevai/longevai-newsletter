def test_create_source_requires_idempotency(client):
    payload = {
        "name": "Buck Institute",
        "method": "rss",
        "config_json": {"url": "https://example.com/feed"},
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "standard",
    }
    resp = client.post("/v1/sources", json=payload)
    assert resp.status_code == 422


def test_create_source_idempotent_replay(client):
    payload = {
        "name": "ERIBA",
        "method": "html",
        "config_json": {"url": "https://example.com/news"},
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "standard",
    }
    headers = {"Idempotency-Key": "source-eriba-1"}
    first = client.post("/v1/sources", json=payload, headers=headers)
    second = client.post("/v1/sources", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


def test_idempotency_conflict(client):
    payload_a = {
        "name": "Source A",
        "method": "rss",
        "config_json": {"url": "https://example.com/a"},
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "standard",
    }
    payload_b = {
        "name": "Source B",
        "method": "rss",
        "config_json": {"url": "https://example.com/b"},
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "standard",
    }
    headers = {"Idempotency-Key": "same-key"}
    first = client.post("/v1/sources", json=payload_a, headers=headers)
    second = client.post("/v1/sources", json=payload_b, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "HTTP_ERROR"


def test_list_sources_envelope(client):
    resp = client.get("/v1/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "error" in body
    assert isinstance(body["data"], list)


def test_metrics_endpoint(client):
    resp = client.get("/v1/metrics/pipeline")
    assert resp.status_code == 200
    assert "today_ingested" in resp.json()["data"]


def test_insight_detail_not_found(client):
    resp = client.get("/v1/insights/99999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "HTTP_ERROR"


def test_ingest_task_status_endpoint(client):
    headers = {"Idempotency-Key": "ingest-task-test"}
    start = client.post("/v1/ingest/run", json={"source_id": None}, headers=headers)
    assert start.status_code == 200
    task_id = start.json()["data"]["task_id"]

    poll = client.get(f"/v1/tasks/{task_id}")
    assert poll.status_code == 200
    assert poll.json()["data"]["task_id"] == task_id
