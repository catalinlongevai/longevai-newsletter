import httpx

from app.core.config import get_settings


async def publish_draft(html: str, title: str = "LongevAI Weekly Brief") -> dict:
    settings = get_settings()
    if not settings.beehiiv_enabled:
        return {"status": "skipped", "reason": "beehiiv not configured"}

    url = f"https://api.beehiiv.com/v2/publications/{settings.beehiiv_publication_id}/posts"
    headers = {
        "Authorization": f"Bearer {settings.beehiiv_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "content_tags": ["longevity", "ai"],
        "status": "draft",
        "html": html,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        return {"status": "error", "error": response.text}
    body = response.json()
    post = body.get("data", body)
    return {
        "status": "ok",
        "external_post_id": post.get("id"),
        "external_url": post.get("web_url") or post.get("url"),
        "body": body,
    }
