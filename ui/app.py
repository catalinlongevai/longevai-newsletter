import os
from datetime import UTC, datetime, timedelta

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")


def _headers(idempotency_key: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if API_AUTH_TOKEN:
        headers["X-API-Key"] = API_AUTH_TOKEN
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _unwrap(response: requests.Response) -> dict:
    payload = response.json()
    return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload


st.set_page_config(page_title="LongevAI Control Plane", layout="wide")
st.title("LongevAI Control Plane")

sources: list[dict] = []
sources_resp = requests.get(f"{API_BASE_URL}/v1/sources", headers=_headers(), timeout=20)
if sources_resp.ok:
    sources = _unwrap(sources_resp)

source_tab, inbox_tab, explorer_tab, bundle_tab, metrics_tab = st.tabs(
    ["Source Management", "Review Inbox", "Pipeline Explorer", "Bundle & Publish", "Metrics"]
)

with source_tab:
    st.subheader("Sources")
    if sources:
        st.dataframe(sources, use_container_width=True)
    else:
        st.warning("No sources available.")

    st.subheader("Source Run History (30-day default)")
    if sources:
        source_lookup = {f"{source['name']} (#{source['id']})": source["id"] for source in sources}
        selected_label = st.selectbox("Select source", list(source_lookup.keys()))
        history_days = st.number_input("History window (days)", min_value=1, max_value=365, value=30)
        history_resp = requests.get(
            f"{API_BASE_URL}/v1/sources/{source_lookup[selected_label]}/runs",
            params={"days": int(history_days), "limit": 200},
            headers=_headers(),
            timeout=20,
        )
        if history_resp.ok:
            st.dataframe(_unwrap(history_resp), use_container_width=True)
        else:
            st.error(history_resp.text)

    st.subheader("Add Source")
    with st.form("add_source"):
        name = st.text_input("Name")
        method = st.selectbox("Method", ["rss", "pubmed", "html", "manual"])
        url = st.text_input("URL")
        selectors = st.text_input("HTML Selectors (comma-separated)")
        pubmed_query = st.text_input("PubMed Query", value='(longevity OR "health span" OR aging)')
        submitted = st.form_submit_button("Create")

        if submitted:
            payload = {
                "name": name,
                "method": method,
                "config_json": {
                    "url": url if url else None,
                    "pubmed_query": pubmed_query,
                    "selectors": [s.strip() for s in selectors.split(",") if s.strip()],
                    "cooldown_seconds": 300,
                },
                "active": True,
                "poll_interval_min": 60,
                "trust_tier": "standard",
            }
            resp = requests.post(
                f"{API_BASE_URL}/v1/sources",
                json=payload,
                headers=_headers(f"source-{datetime.now(UTC).timestamp()}"),
                timeout=20,
            )
            st.write(resp.status_code)
            st.json(resp.json())

    st.subheader("Manual Ingest")
    with st.form("manual_ingest"):
        source_name = st.text_input("Source Name", value="manual-editor")
        manual_url = st.text_input("URL")
        manual_title = st.text_input("Title")
        manual_text = st.text_area("Text", height=180)
        manual_submitted = st.form_submit_button("Queue Manual Item")
        if manual_submitted:
            resp = requests.post(
                f"{API_BASE_URL}/v1/manual-ingest",
                json={
                    "source_name": source_name,
                    "url": manual_url,
                    "title": manual_title or None,
                    "text": manual_text,
                    "operator": "editor",
                },
                headers=_headers(f"manual-{datetime.now(UTC).timestamp()}"),
                timeout=20,
            )
            st.json(resp.json())

    if st.button("Run Ingest"):
        resp = requests.post(
            f"{API_BASE_URL}/v1/ingest/run",
            json={"source_id": None},
            headers=_headers(f"ingest-{datetime.now(UTC).timestamp()}"),
            timeout=20,
        )
        st.json(resp.json())

with inbox_tab:
    st.subheader("Review Inbox")
    col1, col2, col3 = st.columns(3)
    with col1:
        min_novelty = st.slider("Min Novelty", min_value=1, max_value=10, value=1)
    with col2:
        need_verification = st.selectbox("Needs Verification", ["all", "true", "false"])
    with col3:
        order = st.selectbox("Sort Order", ["desc", "asc"])

    params = {
        "min_novelty": min_novelty,
        "order": order,
        "sort": "novelty_score",
        "status": "ready_for_review",
    }
    if need_verification != "all":
        params["needs_human_verification"] = need_verification == "true"

    resp = requests.get(f"{API_BASE_URL}/v1/inbox", params=params, headers=_headers(), timeout=20)
    if resp.ok:
        payload = resp.json()
        data = payload.get("data", {})
        st.caption(f"Items: {data.get('total', 0)}")
        for item in data.get("items", []):
            with st.expander(f"[{item['novelty_score']}] {item['wow_factor'][:120]}"):
                st.write(item["summary_markdown"])
                detail = requests.get(
                    f"{API_BASE_URL}/v1/insights/{item['id']}", headers=_headers(), timeout=20
                )
                if detail.ok:
                    detail_data = _unwrap(detail)
                    st.markdown("Claims")
                    st.dataframe(detail_data.get("claims", []), use_container_width=True)
                    st.markdown("Protocols")
                    st.dataframe(detail_data.get("protocols", []), use_container_width=True)
                    st.markdown("LLM Runs")
                    st.dataframe(detail_data.get("llm_runs", []), use_container_width=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Approve", key=f"approve-{item['id']}"):
                        requests.post(
                            f"{API_BASE_URL}/v1/insights/{item['id']}/approve",
                            headers=_headers(f"approve-{item['id']}-{datetime.now(UTC).timestamp()}"),
                            timeout=20,
                        )
                        st.rerun()
                with col_b:
                    if st.button("Reject", key=f"reject-{item['id']}"):
                        requests.post(
                            f"{API_BASE_URL}/v1/insights/{item['id']}/reject",
                            headers=_headers(f"reject-{item['id']}-{datetime.now(UTC).timestamp()}"),
                            timeout=20,
                        )
                        st.rerun()
    else:
        st.error(resp.text)

with explorer_tab:
    st.subheader("Raw Document Explorer")
    source_options = {"All Sources": None}
    for source in sources:
        source_options[f"{source['name']} (#{source['id']})"] = source["id"]
    selected = st.selectbox("Filter by source", list(source_options.keys()))
    raw_limit = st.slider("Rows", min_value=10, max_value=200, value=50, step=10)

    params = {"limit": raw_limit, "offset": 0}
    selected_source_id = source_options[selected]
    if selected_source_id:
        params["source_id"] = selected_source_id

    raw_resp = requests.get(
        f"{API_BASE_URL}/v1/raw-documents",
        params=params,
        headers=_headers(),
        timeout=20,
    )
    if raw_resp.ok:
        raw_items = _unwrap(raw_resp)
        st.dataframe(raw_items, use_container_width=True)
    else:
        raw_items = []
        st.error(raw_resp.text)

    st.subheader("Raw Document Detail")
    raw_id = st.number_input("Raw Document ID", min_value=1, step=1)
    if st.button("Load Raw Detail"):
        detail_resp = requests.get(
            f"{API_BASE_URL}/v1/raw-documents/{int(raw_id)}",
            headers=_headers(),
            timeout=20,
        )
        if detail_resp.ok:
            detail_data = _unwrap(detail_resp)
            st.write(
                {
                    "source": detail_data["source_name"],
                    "url": detail_data["url"],
                    "status": detail_data["status"],
                    "fetched_at": detail_data["fetched_at"],
                    "title": detail_data.get("title"),
                }
            )
            st.markdown("Raw Text")
            st.text_area("raw_text", value=detail_data.get("raw_text") or "", height=220)
            st.markdown("Normalized Text")
            st.text_area(
                "normalized_text", value=detail_data.get("normalized_text") or "", height=220
            )
            st.markdown("LLM Compression + Prompt")
            for run in detail_data.get("llm_runs", []):
                with st.expander(
                    f"{run['stage']} | {run['provider']}:{run['model']} | v={run['prompt_version']}"
                ):
                    st.write(
                        {
                            "input_tokens": run.get("input_tokens"),
                            "output_tokens": run.get("output_tokens"),
                            "latency_ms": run.get("latency_ms"),
                            "cost_usd": run.get("cost_usd"),
                            "created_at": run.get("created_at"),
                        }
                    )
                    st.markdown("Prompt")
                    st.code(run.get("prompt_text") or "Prompt file not found", language="markdown")
                    st.markdown("Raw Model Output")
                    st.json(run.get("raw_response_json") or {})
        else:
            st.error(detail_resp.text)

with bundle_tab:
    st.subheader("Build Weekly Bundle")
    default_end = datetime.now(UTC)
    default_start = default_end - timedelta(days=7)
    start = st.date_input("Start", default_start.date())
    end = st.date_input("End", default_end.date())

    if st.button("Build Bundle"):
        resp = requests.post(
            f"{API_BASE_URL}/v1/bundles/build",
            json={
                "start": datetime.combine(start, datetime.min.time(), tzinfo=UTC).isoformat(),
                "end": datetime.combine(end, datetime.min.time(), tzinfo=UTC).isoformat(),
            },
            headers=_headers(f"bundle-{datetime.now(UTC).timestamp()}"),
            timeout=20,
        )
        st.json(resp.json())

    bundle_id = st.number_input("Bundle ID", min_value=1, step=1)
    if st.button("Dry Run Publish Check"):
        st.info("Publish is draft-first. Final send is manual in Beehiiv.")

    if st.button("Publish Draft to Beehiiv"):
        st.info("This creates/updates draft content. Send to subscribers manually in Beehiiv UI.")
        resp = requests.post(
            f"{API_BASE_URL}/v1/bundles/{int(bundle_id)}/publish/beehiiv",
            headers=_headers(f"publish-{bundle_id}-{datetime.now(UTC).timestamp()}"),
            timeout=20,
        )
        st.json(resp.json())

with metrics_tab:
    st.subheader("Pipeline Metrics")
    resp = requests.get(f"{API_BASE_URL}/v1/metrics/pipeline", headers=_headers(), timeout=20)
    if resp.ok:
        st.json(resp.json())
    else:
        st.error(resp.text)
