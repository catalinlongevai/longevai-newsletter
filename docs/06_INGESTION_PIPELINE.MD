# Ingestion Pipeline

This document describes ingestion behavior and source adapter details.

## Supported Source Methods

- `rss`
- `pubmed`
- `html`
- `manual`

## Common Steps

1. URL safety and host checks.
2. Source-specific fetch.
3. Content extraction and normalization.
4. Raw snapshot upsert to `raw_documents`.
5. Document creation/upsert and deduplication check.
6. Triage task enqueue.

## RSS Adapter

File: `app/services/ingestion/rss.py`

Capabilities:

- Conditional headers (`If-None-Match`, `If-Modified-Since`)
- Retry with exponential backoff
- Content extraction fallback (`content`, `summary`, `description`)
- ETag and Last-Modified cursor updates

## PubMed Adapter

File: `app/services/ingestion/pubmed.py`

Capabilities:

- `esearch` then `efetch`
- Retry/backoff wrappers
- XML parse guard
- PMID and DOI normalization

## HTML Adapter

File: `app/services/ingestion/html.py`

Capabilities:

- Primary extraction via `trafilatura`
- Selector-driven BeautifulSoup fallback
- Optional Playwright fallback for JS content

## Manual Ingest

Endpoint: `POST /v1/manual-ingest`

Use this for sources behind login walls or content sent manually.

## Safety Controls

File: `app/utils/network.py`

- Protocol restrictions (`http`/`https` only)
- Host allowlist support
- Private/loopback/link-local/reserved IP blocking
- No auto-follow redirects in adapters

## Operational Source Health

`sources` table tracks:

- `last_scraped_at`
- `last_success_at`
- `last_error`
- `failure_count`
