import argparse
from collections import Counter

from app.db.session import get_session_maker
from app.models.entities import Source
try:
    from scripts.source_catalog import SOURCE_CATALOG
except ModuleNotFoundError:
    from source_catalog import SOURCE_CATALOG  # type: ignore


def upsert_sources(dry_run: bool = False, disable_unmanaged: bool = False) -> dict[str, int]:
    db = get_session_maker()()
    stats: Counter[str] = Counter()
    catalog_names = {item["name"] for item in SOURCE_CATALOG}

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

        if disable_unmanaged:
            unmanaged_sources = (
                db.query(Source)
                .filter(Source.name.notin_(catalog_names), Source.active.is_(True))
                .all()
            )
            for unmanaged in unmanaged_sources:
                unmanaged.active = False
                stats["disabled_unmanaged"] += 1

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
    parser.add_argument(
        "--disable-unmanaged",
        action="store_true",
        help="Disable active sources that are not present in scripts/source_catalog.py",
    )
    args = parser.parse_args()

    stats = upsert_sources(dry_run=args.dry_run, disable_unmanaged=args.disable_unmanaged)
    print(f"Seed completed: {stats}")


if __name__ == "__main__":
    main()
