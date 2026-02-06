from scripts.source_catalog import SOURCE_CATALOG


def test_source_catalog_contains_requested_names():
    names = {item["name"] for item in SOURCE_CATALOG}
    expected = {
        "Peter Diamandis (Longevity Insider)",
        "Peter Attia",
        "Huberman Lab",
        "Chris (LinkedIn)",
        "Buck Institute for Research on Aging",
        "ERIBA",
        "Aging Institute",
        "Healthy Longevity",
        "PubMed Longevity",
        "Medical Press",
        "In Silico Medicine",
        "Longevity Technology",
    }
    assert expected.issubset(names)


def test_ready_sources_are_active_and_scaffold_are_inactive():
    for item in SOURCE_CATALOG:
        status = item["config_json"]["onboarding_status"]
        if status == "ready":
            assert item["active"] is True
        if status == "scaffold":
            assert item["active"] is False
