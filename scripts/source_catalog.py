from app.models.entities import SourceMethod

# Canonical source catalog for MVP onboarding.
# onboarding_status:
# - ready: auto-ingest now
# - scaffold: keep inactive; needs follow-up implementation or source clarification
SOURCE_CATALOG = [
    {
        "name": "Peter Attia",
        "method": SourceMethod.rss,
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "influencer",
        "config_json": {
            "url": "https://peterattiamd.com/feed/",
            "cooldown_seconds": 1800,
            "onboarding_status": "ready",
            "onboarding_notes": "High-value prevention content via RSS.",
        },
    },
    {
        "name": "Buck Institute for Research on Aging",
        "method": SourceMethod.rss,
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "institution",
        "config_json": {
            "url": "https://www.buckinstitute.org/feed/",
            "cooldown_seconds": 1800,
            "onboarding_status": "ready",
            "onboarding_notes": "Institutional announcements via RSS.",
        },
    },
    {
        "name": "PubMed Longevity",
        "method": SourceMethod.pubmed,
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "scientific",
        "config_json": {
            "pubmed_query": '(longevity OR "health span" OR aging) AND ("last 7 days"[PDat])',
            "cooldown_seconds": 3600,
            "onboarding_status": "ready",
            "onboarding_notes": "Core scientific feed for weekly novelty scanning.",
        },
    },
    {
        "name": "Longevity Technology",
        "method": SourceMethod.rss,
        "active": True,
        "poll_interval_min": 60,
        "trust_tier": "news",
        "config_json": {
            "url": "https://longevity.technology/feed/",
            "cooldown_seconds": 1800,
            "onboarding_status": "ready",
            "onboarding_notes": "Competitor/industry watcher feed via RSS.",
        },
    },
    {
        "name": "Peter Diamandis (Longevity Insider)",
        "method": SourceMethod.manual,
        "active": False,
        "poll_interval_min": 1440,
        "trust_tier": "influencer",
        "config_json": {
            "url": "https://www.longevityinsider.org/",
            "onboarding_status": "scaffold",
            "onboarding_notes": "Site redirects to subscription flow; use manual ingest from newsletter issues.",
        },
    },
    {
        "name": "Huberman Lab",
        "method": SourceMethod.manual,
        "active": False,
        "poll_interval_min": 1440,
        "trust_tier": "influencer",
        "config_json": {
            "url": "https://www.hubermanlab.com/",
            "onboarding_status": "scaffold",
            "onboarding_notes": "No stable RSS endpoint confirmed; use manual ingest or implement sitemap-based monitor.",
        },
    },
    {
        "name": "Chris (LinkedIn)",
        "method": SourceMethod.manual,
        "active": False,
        "poll_interval_min": 1440,
        "trust_tier": "influencer",
        "config_json": {
            "onboarding_status": "scaffold",
            "onboarding_notes": "Identity/URL not finalized; LinkedIn is anti-scraping so keep manual ingestion.",
        },
    },
    {
        "name": "ERIBA",
        "method": SourceMethod.html,
        "active": False,
        "poll_interval_min": 240,
        "trust_tier": "institution",
        "config_json": {
            "url": "https://eriba.umcg.nl/future-events/news/",
            "selectors": ["article", "h2", ".entry-content p"],
            "cooldown_seconds": 7200,
            "onboarding_status": "scaffold",
            "onboarding_notes": "Domain is reachable; needs collection-diff monitor for multi-article detection.",
        },
    },
    {
        "name": "Aging Institute",
        "method": SourceMethod.manual,
        "active": False,
        "poll_interval_min": 1440,
        "trust_tier": "institution",
        "config_json": {
            "onboarding_status": "scaffold",
            "onboarding_notes": "Organization reference is ambiguous; finalize canonical source URL before automation.",
        },
    },
    {
        "name": "Healthy Longevity",
        "method": SourceMethod.manual,
        "active": False,
        "poll_interval_min": 1440,
        "trust_tier": "institution",
        "config_json": {
            "onboarding_status": "scaffold",
            "onboarding_notes": "National initiative reference is ambiguous; confirm exact target domain(s).",
        },
    },
    {
        "name": "Medical Press",
        "method": SourceMethod.manual,
        "active": False,
        "poll_interval_min": 1440,
        "trust_tier": "news",
        "config_json": {
            "url": "https://medicalxpress.com/",
            "onboarding_status": "scaffold",
            "onboarding_notes": "RSS endpoints currently block/return errors in automation checks; use manual until stable endpoint is confirmed.",
        },
    },
    {
        "name": "In Silico Medicine",
        "method": SourceMethod.html,
        "active": False,
        "poll_interval_min": 240,
        "trust_tier": "industry",
        "config_json": {
            "url": "https://www.insilico.com/news",
            "selectors": ["article", "h2", "p"],
            "cooldown_seconds": 7200,
            "onboarding_status": "scaffold",
            "onboarding_notes": "Site uses anti-bot protection; keep inactive until Playwright + anti-bot strategy is validated.",
        },
    },
]
