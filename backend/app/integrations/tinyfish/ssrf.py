"""Reject private/metadata destinations before sending URLs to TinyFish."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.integrations.tinyfish.exceptions import TinyFishSSRFError

_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.google.com",
    "169.254.169.254",
}


def validate_public_https_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise TinyFishSSRFError("Empty URL")
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise TinyFishSSRFError("Only https URLs are allowed")
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_HOSTS:
        raise TinyFishSSRFError("Host is not allowed")
    if host.endswith(".local") or host.endswith(".internal"):
        raise TinyFishSSRFError("Host is not allowed")
    _reject_private_ip(host)
    return raw


def _reject_private_ip(host: str) -> None:
    try:
        ip = ipaddress.ip_address(host)
        if _is_bad_ip(ip):
            raise TinyFishSSRFError("Private or reserved IP is not allowed")
        return
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise TinyFishSSRFError(f"Could not resolve host: {host}") from exc
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip = ipaddress.ip_address(sockaddr[0])
        if _is_bad_ip(ip):
            raise TinyFishSSRFError("Host resolves to a private or reserved IP")


def _is_bad_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
