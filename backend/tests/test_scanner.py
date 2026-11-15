"""Redirect-guard tests that do not start a real browser."""

from __future__ import annotations

import socket
import unittest
from unittest.mock import patch

from backend.scanner import ScanBlockedError, validate_redirect_target


def public_dns(*_args: object, **_kwargs: object) -> list[tuple]:
    return [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 0))
    ]


class RedirectGuardTests(unittest.TestCase):
    def test_follows_relative_public_redirect(self) -> None:
        with patch("backend.scan_logic.socket.getaddrinfo", side_effect=public_dns):
            target = validate_redirect_target("https://example.com/a", "/b")
        self.assertEqual(target, "https://example.com/b")

    def test_blocks_redirect_to_private_ip(self) -> None:
        with self.assertRaisesRegex(ValueError, "public IP"):
            validate_redirect_target("https://example.com/", "http://127.0.0.1/admin")

    def test_allows_http_to_https_redirect(self) -> None:
        with patch("backend.scan_logic.socket.getaddrinfo", side_effect=public_dns):
            target = validate_redirect_target("http://example.com/", "https://example.com/")
        self.assertEqual(target, "https://example.com/")

    def test_blocks_https_to_http_downgrade(self) -> None:
        with (
            patch("backend.scan_logic.socket.getaddrinfo", side_effect=public_dns),
            self.assertRaises(ScanBlockedError),
        ):
            validate_redirect_target("https://example.com/", "http://example.com/")


if __name__ == "__main__":
    unittest.main()
