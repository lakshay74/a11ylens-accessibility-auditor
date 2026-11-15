"""Input validation and deterministic report scoring for web scans."""

from __future__ import annotations

import ipaddress
import socket
from collections import Counter
from urllib.parse import urlsplit, urlunsplit
from typing import Any


MAX_URL_LENGTH = 2048
MAX_RULE_PENALTY_NODES = 5
IMPACT_WEIGHTS = {
    "critical": 12,
    "serious": 8,
    "moderate": 4,
    "minor": 1,
}
IMPACT_ORDER = ("critical", "serious", "moderate", "minor")
LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".test", ".invalid", ".example")
LOCAL_HOSTS = {"localhost", "metadata", "instance-data"}
SPECIAL_CLOUD_IPS = {
    ipaddress.ip_address("168.63.129.16"),  # Azure platform virtual IP
    ipaddress.ip_address("169.254.169.254"),  # Common cloud metadata endpoint
    ipaddress.ip_address("169.254.170.2"),  # AWS container credential endpoint
    ipaddress.ip_address("100.100.100.200"),  # Alibaba Cloud metadata endpoint
}


def _public_addresses(hostname: str, port: int) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a host and reject it if any answer is not globally routable."""

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None

    if literal is not None:
        if isinstance(literal, ipaddress.IPv6Address) and literal.ipv4_mapped:
            literal = literal.ipv4_mapped
        addresses = [literal]
    else:
        try:
            answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except OSError as error:
            raise ValueError("The URL host could not be resolved.") from error
        addresses = []
        for answer in answers:
            try:
                resolved = ipaddress.ip_address(answer[4][0].split("%", 1)[0])
                if isinstance(resolved, ipaddress.IPv6Address) and resolved.ipv4_mapped:
                    resolved = resolved.ipv4_mapped
                addresses.append(resolved)
            except ValueError as error:
                raise ValueError("The URL host resolved to an invalid address.") from error

    if any(address in SPECIAL_CLOUD_IPS for address in addresses):
        raise ValueError("Cloud metadata and platform addresses cannot be scanned.")
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("The URL host must resolve only to public IP addresses.")
    return addresses


def validate_public_url(raw_url: str) -> str:
    """Return a normalized HTTP(S) URL after checking its host and DNS answers.

    Call this for the initial URL and again for every browser request/redirect.
    Browser routing should block the request whenever this raises ``ValueError``.
    """

    if not isinstance(raw_url, str):
        raise ValueError("Enter a valid HTTP or HTTPS URL.")
    url = raw_url.strip()
    if not url or len(url) > MAX_URL_LENGTH or any(ord(char) < 32 for char in url):
        raise ValueError("Enter a URL under 2,048 characters with no control characters.")

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("The URL is malformed.") from error

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs can be scanned.")
    if not parsed.netloc or parsed.username is not None or parsed.password is not None:
        raise ValueError("Enter a public URL without embedded credentials.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("The URL must include a host name.")
    hostname = hostname.rstrip(".").lower()
    if "%" in hostname:
        raise ValueError("Scoped IP addresses cannot be scanned.")
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("The URL host name is invalid.") from error
    if ascii_hostname in LOCAL_HOSTS or ascii_hostname.endswith(LOCAL_SUFFIXES):
        raise ValueError("Local and internal host names cannot be scanned.")

    resolved_port = port or (443 if scheme == "https" else 80)
    if resolved_port < 1 or resolved_port > 65535:
        raise ValueError("The URL port is invalid.")
    _public_addresses(ascii_hostname, resolved_port)

    # Keep the supplied authority intact (including IPv6 brackets/port) while
    # normalizing the scheme and dropping fragments, which are never sent.
    return urlunsplit((scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


def score_report(violations: list[dict[str, Any]]) -> dict[str, Any]:
    """Score a scan from 0 to 100 using axe impact and capped affected-node counts.

    Each axe rule contributes its impact weight multiplied by up to five affected
    nodes. Multiple rules can count the same element because axe reports rules.
    Missing/unrecognized impact uses the minor weight and is grouped under minor.
    """

    impact_counts: Counter[str] = Counter()
    affected_elements = 0
    penalty = 0

    for violation in violations:
        impact = str(violation.get("impact") or "minor").lower()
        if impact not in IMPACT_WEIGHTS:
            impact = "minor"
        nodes = violation.get("nodes")
        node_count = len(nodes) if isinstance(nodes, list) else 0
        reported_count = violation.get("totalNodes")
        if isinstance(reported_count, int) and reported_count >= 0:
            node_count = reported_count
        node_count = max(node_count, 0)
        impact_counts[impact] += node_count
        affected_elements += node_count
        penalty += IMPACT_WEIGHTS[impact] * min(node_count, MAX_RULE_PENALTY_NODES)

    return {
        "score": max(0, 100 - penalty),
        "penalty": penalty,
        "violation_rules": len(violations),
        "affected_elements": affected_elements,
        "impact_counts": {impact: impact_counts[impact] for impact in IMPACT_ORDER},
    }
