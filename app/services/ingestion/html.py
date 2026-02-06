from __future__ import annotations

import httpx
import trafilatura
from bs4 import BeautifulSoup
from typing import Any

from app.core.config import get_settings
from app.services.ingestion.common import IngestedItem
from app.utils.network import assert_allowed_url

try:
    from playwright.async_api import async_playwright
except Exception:  # noqa: BLE001
    async_playwright = None  # type: ignore[assignment]


def _extract_with_bs4(html: str, selectors: list[str] | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if selectors:
        selected: list[Any] = []
        for selector in selectors:
            selected.extend(soup.select(selector))
        text = " ".join(node.get_text(" ", strip=True) for node in selected)
        if text:
            return text
    return " ".join(
        el.get_text(" ", strip=True) for el in soup.find_all(["article", "h1", "h2", "h3", "p"])
    )


async def _fetch_dynamic_html(url: str) -> str | None:
    if async_playwright is None:
        return None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return await page.content()
        finally:
            await browser.close()


async def fetch_html_items(url: str, selectors: list[str] | None = None) -> list[IngestedItem]:
    assert_allowed_url(url)
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.ingest_http_timeout_seconds, follow_redirects=False) as client:
        response = await client.get(url)
        response.raise_for_status()

    html = response.text
    text = trafilatura.extract(html)
    if not text:
        text = _extract_with_bs4(html, selectors)

    # Optional JS fallback.
    if not text:
        dynamic_html = await _fetch_dynamic_html(url)
        if dynamic_html:
            text = trafilatura.extract(dynamic_html) or _extract_with_bs4(dynamic_html, selectors)
            html = dynamic_html

    return [
        IngestedItem(
            external_id=url,
            url=url,
            title=None,
            raw_text=text,
            raw_html=html,
            http_meta={"status_code": response.status_code, "selector_profile": selectors or []},
        )
    ]
