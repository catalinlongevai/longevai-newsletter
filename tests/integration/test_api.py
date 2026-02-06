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


def test_source_run_history_endpoint(client):
    create_headers = {"Idempotency-Key": "source-run-history-source"}
    source_payload = {
        "name": "Manual History Source",
        "method": "manual",
        "config_json": {},
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "manual",
    }
    created = client.post("/v1/sources", json=source_payload, headers=create_headers)
    assert created.status_code == 200
    source_id = created.json()["data"]["id"]

    run_headers = {"Idempotency-Key": "source-run-history-trigger"}
    run_resp = client.post("/v1/ingest/run", json={"source_id": source_id}, headers=run_headers)
    assert run_resp.status_code == 200

    history = client.get(f"/v1/sources/{source_id}/runs?days=30&limit=50")
    assert history.status_code == 200
    runs = history.json()["data"]
    assert len(runs) >= 1
    assert runs[0]["source_id"] == source_id


def test_raw_document_explorer_endpoints(client):
    headers = {"Idempotency-Key": "manual-ingest-raw-doc"}
    payload = {
        "source_name": "Manual Explorer Source",
        "url": "https://example.com/manual-longevity-item",
        "title": "Manual longevity extract",
        "text": "Longevity intervention study with aging biomarkers and protocol details.",
        "operator": "editor",
    }
    resp = client.post("/v1/manual-ingest", json=payload, headers=headers)
    assert resp.status_code == 200

    list_resp = client.get("/v1/raw-documents?limit=50&offset=0")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert len(items) >= 1
    raw_id = items[0]["id"]

    detail_resp = client.get(f"/v1/raw-documents/{raw_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert "raw_text" in detail
    assert "llm_runs" in detail


def test_insight_detail_includes_prompt_text(client):
    headers = {"Idempotency-Key": "manual-ingest-prompt-detail"}
    payload = {
        "source_name": "Manual Prompt Source",
        "url": "https://example.com/manual-prompt-item",
        "title": "Prompt detail item",
        "text": "Aging and longevity findings with claim evidence and protocol notes.",
        "operator": "editor",
    }
    ingest = client.post("/v1/manual-ingest", json=payload, headers=headers)
    assert ingest.status_code == 200

    inbox = client.get("/v1/inbox?status=ready_for_review&limit=50&offset=0")
    assert inbox.status_code == 200
    items = inbox.json()["data"]["items"]
    assert len(items) >= 1
    insight_id = items[0]["id"]

    detail = client.get(f"/v1/insights/{insight_id}")
    assert detail.status_code == 200
    llm_runs = detail.json()["data"]["llm_runs"]
    assert len(llm_runs) >= 1
    assert "prompt_text" in llm_runs[0]
