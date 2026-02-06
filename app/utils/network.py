import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import get_settings


class HostNotAllowedError(ValueError):
    pass


class UnsafeUrlError(ValueError):
    pass


def _is_private_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    for info in infos:
        ip = info[4][0]
        parsed = ipaddress.ip_address(ip)
        if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved:
            return True
    return False


def assert_allowed_url(url: str) -> None:
    settings = get_settings()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Only http/https URLs are supported")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeUrlError("URL host is missing")
    if _is_private_host(host):
        raise UnsafeUrlError("Resolved host is private or unsafe")

    allowlist = settings.allowed_fetch_host_list
    if not allowlist:
        return
    if host not in allowlist:
        raise HostNotAllowedError(f"Host not in allowlist: {host}")
