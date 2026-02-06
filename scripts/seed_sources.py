import argparse
from collections import Counter

from app.db.session import get_session_maker
from app.models.entities import Source
try:
    from scripts.source_catalog import SOURCE_CATALOG
except ModuleNotFoundError:
    from source_catalog import SOURCE_CATALOG  # type: ignore


def upsert_sources(dry_run: bool = False) -> dict[str, int]:
    db = get_session_maker()()
    stats: Counter[str] = Counter()

    try:
        for item in SOURCE_CATALOG:
            existing = db.query(Source).filter(Source.name == item["name"]).one_or_none()
            if existing:
                existing.method = item["method"]
                existing.config_json = item["config_json"]
                existing.active = item["active"]
                existing.poll_interval_min = item["poll_interval_min"]
                existing.trust_tier = item["trust_tier"]
                stats["updated"] += 1
            else:
                db.add(
                    Source(
                        name=item["name"],
                        method=item["method"],
                        config_json=item["config_json"],
                        active=item["active"],
                        poll_interval_min=item["poll_interval_min"],
                        trust_tier=item["trust_tier"],
                    )
                )
                stats["created"] += 1

        if dry_run:
            db.rollback()
            stats["dry_run"] = 1
        else:
            db.commit()

        return dict(stats)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed LongevAI source catalog")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print changes without committing")
    args = parser.parse_args()

    stats = upsert_sources(dry_run=args.dry_run)
    print(f"Seed completed: {stats}")


if __name__ == "__main__":
    main()
