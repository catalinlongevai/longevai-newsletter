import pytest

from app.utils.network import UnsafeUrlError, assert_allowed_url


def test_blocks_unsafe_scheme():
    with pytest.raises(UnsafeUrlError):
        assert_allowed_url("file:///etc/passwd")


def test_allows_https_domain_when_allowlist_empty():
    assert_allowed_url("https://example.com/article")
