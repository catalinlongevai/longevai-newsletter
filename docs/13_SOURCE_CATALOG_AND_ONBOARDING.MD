# Source Catalog and Onboarding Status

This document tracks the source list requested by editorial and what is implemented now.

## Policy

- `ready`: source is active and auto-ingested today.
- `scaffold`: source exists in DB as inactive with method/config notes, ready for next implementation step.

## Active Now (Highest Value + Simplest)

1. Peter Attia (`rss`)
2. Buck Institute for Research on Aging (`rss`)
3. PubMed Longevity (`pubmed`)
4. Longevity Technology (`rss`)

These are auto-enabled by `make seed`.

## Scaffolded Now (Inactive)

1. Peter Diamandis (Longevity Insider) (`manual`)
2. Huberman Lab (`manual`)
3. Chris (LinkedIn) (`manual`)
4. ERIBA (`html`)
5. Aging Institute (`manual`)
6. Healthy Longevity (`manual`)
7. Medical Press (`manual`)
8. In Silico Medicine (`html`)

## Why Some Are Scaffolded

- Ambiguous target identity/URL (Aging Institute, Healthy Longevity, Chris).
- Anti-bot/protected sites (In Silico, LinkedIn workflows, MedicalXpress behavior).
- No stable RSS endpoint validated (Huberman Lab).
- HTML monitor in current MVP is single-page extraction and needs collection-diff support for reliable "new article" detection (ERIBA).

## How `make seed` Behaves

`make seed` now performs an **upsert** against the canonical source catalog.

- Existing source rows with same `name` are updated to match catalog method/config/active status.
- Missing rows are created.

Dry run:

```bash
API_AUTH_TOKEN=dev-token .venv/bin/python scripts/seed_sources.py --dry-run
```

Disable non-catalog active sources (recommended when syncing to the approved source set):

```bash
API_AUTH_TOKEN=dev-token .venv/bin/python scripts/seed_sources.py --disable-unmanaged
```

## Next Implementation Steps Per Scaffolded Group

### LinkedIn / Manual-only sources

- Keep `manual` method.
- Standardize operator workflow in UI (`POST /v1/manual-ingest`).
- Add editorial SOP for weekly capture.

### ERIBA and other HTML institutions

- Implement collection-page diffing:
  - Parse list page for article links.
  - Store seen link IDs per source cursor.
  - Fetch only unseen links and write one `raw_document` per article.

### Medical Press / anti-bot sources

- Add source-specific HTTP headers and throttling profile.
- Use Playwright fallback queue where permitted.
- Keep inactive until stability threshold is met.

### Huberman

- Confirm canonical machine-readable feed path (RSS/Atom/JSON feed) or fall back to newsletter/manual pathway.

## Source Catalog Location

Canonical list used by seeding:

- `scripts/source_catalog.py`
