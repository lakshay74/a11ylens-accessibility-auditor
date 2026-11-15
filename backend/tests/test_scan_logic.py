"""Focused unit tests for scan URL safety and A11yLens score calculation."""

from __future__ import annotations

import socket
import unittest
from unittest.mock import patch

from backend.scan_logic import score_report, validate_public_url


def _public_dns(*_args: object, **_kwargs: object) -> list[tuple]:
    return [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 0))
    ]


class URLValidationTests(unittest.TestCase):
    def test_accepts_public_http_url_and_drops_fragment(self) -> None:
        with patch("backend.scan_logic.socket.getaddrinfo", side_effect=_public_dns):
            self.assertEqual(
                validate_public_url("HTTPS://Example.COM/path?q=1#section"),
                "https://Example.COM/path?q=1",
            )

    def test_rejects_non_http_scheme_without_dns_lookup(self) -> None:
        with patch("backend.scan_logic.socket.getaddrinfo") as resolver:
            with self.assertRaises(ValueError):
                validate_public_url("file:///etc/passwd")
            resolver.assert_not_called()

    def test_rejects_local_names_and_credentials(self) -> None:
        for url in ("http://localhost/", "http://metadata.google.internal/", "https://user:pass@example.com/"):
            with self.subTest(url=url), patch("backend.scan_logic.socket.getaddrinfo", side_effect=_public_dns):
                with self.assertRaises(ValueError):
                    validate_public_url(url)

    def test_rejects_private_ip_literal(self) -> None:
        with self.assertRaisesRegex(ValueError, "public IP"):
            validate_public_url("http://127.0.0.1/")

    def test_rejects_special_cloud_service_ip_even_if_globally_routed(self) -> None:
        for address in ("168.63.129.16", "::ffff:168.63.129.16"):
            with self.subTest(address=address), self.assertRaisesRegex(ValueError, "metadata"):
                validate_public_url(f"https://[{address}]/" if ":" in address else f"https://{address}/")

    def test_rejects_hostname_with_any_private_dns_answer(self) -> None:
        mixed_answers = _public_dns() + [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.1.2.3", 0))
        ]
        with patch("backend.scan_logic.socket.getaddrinfo", return_value=mixed_answers):
            with self.assertRaisesRegex(ValueError, "public IP"):
                validate_public_url("https://mixed.example.com/")

    def test_rejects_unresolvable_hostname(self) -> None:
        with patch("backend.scan_logic.socket.getaddrinfo", side_effect=socket.gaierror("not found")):
            with self.assertRaisesRegex(ValueError, "could not be resolved"):
                validate_public_url("https://missing.example.com/")


class ScoreTests(unittest.TestCase):
    def test_score_and_impact_counts_are_deterministic(self) -> None:
        result = score_report([
            {"impact": "critical", "nodes": [{}, {}]},
            {"impact": "moderate", "nodes": [{}]},
        ])
        self.assertEqual(result, {
            "score": 72,
            "penalty": 28,
            "violation_rules": 2,
            "affected_elements": 3,
            "impact_counts": {"critical": 2, "serious": 0, "moderate": 1, "minor": 0},
        })

    def test_caps_each_rule_at_five_nodes_and_score_at_zero(self) -> None:
        result = score_report([{"impact": "serious", "nodes": [{} for _ in range(20)], "totalNodes": 20}] * 3)
        self.assertEqual(result["penalty"], 120)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["affected_elements"], 60)

    def test_uses_full_axe_node_count_when_response_nodes_are_capped(self) -> None:
        result = score_report([{"impact": "moderate", "nodes": [{} for _ in range(25)], "totalNodes": 90}])
        self.assertEqual(result["score"], 80)
        self.assertEqual(result["affected_elements"], 90)

    def test_unknown_impact_is_counted_as_minor(self) -> None:
        result = score_report([{"impact": "unknown", "nodes": [{}]}])
        self.assertEqual(result["score"], 99)
        self.assertEqual(result["impact_counts"]["minor"], 1)

    def test_empty_node_list_does_not_invent_an_affected_element(self) -> None:
        result = score_report([{"impact": "serious", "nodes": []}])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["affected_elements"], 0)


if __name__ == "__main__":
    unittest.main()
