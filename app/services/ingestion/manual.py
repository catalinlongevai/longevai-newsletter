from app.services.ingestion.common import IngestedItem


def create_manual_item(url: str, text: str, title: str | None = None, operator: str = "editor") -> IngestedItem:
    return IngestedItem(
        external_id=url,
        url=url,
        title=title,
        raw_text=text,
        raw_html=text,
        http_meta={"manual": True, "operator": operator},
    )
