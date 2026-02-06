from app.services.ingestion.pubmed import _extract_doi


def test_extract_doi_from_text():
    text = "Results available at doi:10.1234/ABCD.567"
    doi = _extract_doi(text)
    assert doi == "10.1234/ABCD.567"


def test_extract_doi_none_when_missing():
    assert _extract_doi("no doi here") is None
