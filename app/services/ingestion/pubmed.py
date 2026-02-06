import re
import xml.etree.ElementTree as ET

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.ingestion.common import IngestedItem

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
async def _eutils_get(path: str, params: dict) -> httpx.Response:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.ingest_http_timeout_seconds) as client:
        response = await client.get(f"{EUTILS}/{path}", params=params)
    response.raise_for_status()
    return response


def _extract_doi(text: str) -> str | None:
    match = DOI_PATTERN.search(text or "")
    return match.group(0) if match else None


async def fetch_pubmed_items(query: str, retmax: int = 20) -> list[IngestedItem]:
    settings = get_settings()
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "sort": "pub+date",
        "retmax": retmax,
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key

    search = await _eutils_get("esearch.fcgi", params)
    ids = search.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
    }
    if settings.ncbi_api_key:
        fetch_params["api_key"] = settings.ncbi_api_key
    raw = await _eutils_get("efetch.fcgi", fetch_params)

    try:
        root = ET.fromstring(raw.text)
    except ET.ParseError:
        return []

    items: list[IngestedItem] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle") or ""
        abstract_nodes = article.findall(".//Abstract/AbstractText")
        abstract = "\n".join(["".join(node.itertext()) for node in abstract_nodes])
        if not pmid:
            continue

        doi = article.findtext(".//ArticleId[@IdType='doi']") or _extract_doi(abstract)
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        external_id = f"pmid:{pmid}"
        if doi:
            external_id = f"doi:{doi.lower()}"

        items.append(
            IngestedItem(
                external_id=external_id,
                url=url,
                title=title,
                raw_text=abstract,
                raw_html=abstract,
                http_meta={"provider": "pubmed", "pmid": pmid, "doi": doi},
            )
        )
    return items
