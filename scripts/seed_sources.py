from app.db.session import get_session_maker
from app.models.entities import Source, SourceMethod

SEED_SOURCES = [
    {
        "name": "Peter Attia",
        "method": SourceMethod.rss,
        "config_json": {"url": "https://peterattiamd.com/feed/", "cooldown_seconds": 1800},
    },
    {
        "name": "Huberman Lab",
        "method": SourceMethod.rss,
        "config_json": {"url": "https://www.hubermanlab.com/feed", "cooldown_seconds": 1800},
    },
    {
        "name": "PubMed Longevity",
        "method": SourceMethod.pubmed,
        "config_json": {
            "pubmed_query": '(longevity OR "health span" OR aging) AND ("last 7 days"[PDat])',
            "cooldown_seconds": 3600,
        },
    },
    {
        "name": "Medical Xpress Gerontology",
        "method": SourceMethod.rss,
        "config_json": {
            "url": "https://medicalxpress.com/rss-feed/gerontology-genetics-news/",
            "cooldown_seconds": 1800,
        },
    },
]


def main() -> None:
    db = get_session_maker()()
    try:
        for item in SEED_SOURCES:
            exists = db.query(Source).filter(Source.name == item["name"]).one_or_none()
            if exists:
                continue
            db.add(
                Source(
                    name=item["name"],
                    method=item["method"],
                    config_json=item["config_json"],
                    active=True,
                    poll_interval_min=60,
                    trust_tier="standard",
                )
            )
        db.commit()
        print("Seed completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
