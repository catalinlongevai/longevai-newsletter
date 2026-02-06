from datetime import datetime

from pydantic import BaseModel, Field


class IngestedItem(BaseModel):
    external_id: str
    url: str
    title: str | None = None
    published_at: datetime | None = None
    raw_text: str | None = None
    raw_html: str | None = None
    http_meta: dict = Field(default_factory=dict)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())
