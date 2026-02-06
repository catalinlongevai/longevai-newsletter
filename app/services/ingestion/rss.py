from datetime import datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.ingestion.common import IngestedItem
from app.utils.network import assert_allowed_url


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
async def _fetch(url: str, headers: dict) -> httpx.Response:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.ingest_http_timeout_seconds, follow_redirects=False) as client:
        response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response


def _extract_body(entry: dict) -> str:
    html = (
        entry.get("content", [{}])[0].get("value")
        if isinstance(entry.get("content"), list) and entry.get("content")
        else None
    )
    html = html or entry.get("summary") or entry.get("description") or ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


async def fetch_rss_items(
    url: str, etag: str | None = None, last_modified: str | None = None
) -> tuple[list[IngestedItem], dict]:
    assert_allowed_url(url)
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    response = await _fetch(url, headers)
    if response.status_code == 304:
        return [], {"etag": etag, "last_modified": last_modified}

    feed = feedparser.parse(response.text)
    items: list[IngestedItem] = []
    for entry in feed.entries:
        link = entry.get("link")
        if not link:
            continue
        published = None
        if entry.get("published_parsed"):
            published = datetime(*entry.published_parsed[:6])
        body = _extract_body(entry)
        items.append(
            IngestedItem(
                external_id=entry.get("id") or entry.get("guid") or link,
                url=link,
                title=entry.get("title"),
                published_at=published,
                raw_text=body,
                raw_html=entry.get("summary") or entry.get("description") or "",
                http_meta={
                    "etag": response.headers.get("etag"),
                    "last_modified": response.headers.get("last-modified"),
                    "feed_bozo": int(getattr(feed, "bozo", 0)),
                },
            )
        )

    return items, {
        "etag": response.headers.get("etag"),
        "last_modified": response.headers.get("last-modified"),
    }
