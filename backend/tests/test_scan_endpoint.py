"""Mocked endpoint-handler tests that do not launch Chromium or open sockets."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend import main


async def immediate_to_thread(function, *args, **kwargs):
    """Run the mocked validation inline so this unit test needs no local socket."""
    return function(*args, **kwargs)


async def immediate_wait_for(awaitable, timeout=None):
    return await awaitable


def run_immediate(coroutine):
    """Drive this endpoint's fully mocked coroutine to completion."""
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("A mocked endpoint operation unexpectedly yielded to the event loop.")


def fake_request(client_ip: str) -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=client_ip))


class ScanEndpointTests(unittest.TestCase):
    def test_api_root_points_to_the_web_app(self) -> None:
        with patch("backend.main.FRONTEND_ORIGIN", ""):
            self.assertEqual(
                main.root(),
                {
                    "service": "A11yLens API",
                    "status": "ok",
                    "web_app": "http://localhost:4173/",
                    "health": "/health",
                },
            )

    def invoke_scan(self, client_ip: str, url: str = "https://example.com/"):
        with (
            patch("backend.main.asyncio.to_thread", new=immediate_to_thread),
            patch("backend.main.asyncio.wait_for", new=immediate_wait_for),
        ):
            return run_immediate(main.scan(main.ScanRequest(url=url), fake_request(client_ip)))

    def test_returns_mocked_axe_results_and_score(self) -> None:
        mocked_scan = {
            "url": "https://example.com/",
            "title": "Example page",
            "violations": [
                {
                    "id": "image-alt",
                    "impact": "critical",
                    "description": "Images must have alternate text",
                    "helpUrl": "https://dequeuniversity.com/rules/axe/4.14/image-alt",
                    "nodes": [{"target": ["img"], "html": "<img src='x'>", "failureSummary": "Add an alt attribute."}],
                    "totalNodes": 1,
                }
            ],
            "scan_limits": {"requests_checked": 3, "response_bytes": 1024, "nodes_returned_per_rule": 25},
        }
        with (
            patch("backend.main.validate_public_url", return_value="https://example.com/"),
            patch("backend.main.scan_with_playwright", new=AsyncMock(return_value=mocked_scan)),
            patch("backend.main.enrich_scan_violations", new=AsyncMock(return_value=(mocked_scan["violations"], {"provider": "local", "groq_findings": 0, "local_fallbacks": 0, "local_findings": 1}))),
        ):
            body = self.invoke_scan("198.51.100.11")

        self.assertEqual(body["score"]["score"], 88)
        self.assertEqual(body["score"]["affected_elements"], 1)
        self.assertEqual(body["violations"][0]["id"], "image-alt")
        self.assertIn("not an official WCAG rating", body["score_note"])
        self.assertFalse(body["saved"])

    def test_saves_a_query_redacted_report_and_returns_share_link(self) -> None:
        mocked_scan = {
            "url": "https://example.com/library?access_token=secret#top",
            "title": "Library page",
            "violations": [],
        }
        report_id = "a" * 32
        with (
            patch("backend.main.validate_public_url", return_value="https://example.com/library?access_token=secret"),
            patch("backend.main.scan_with_playwright", new=AsyncMock(return_value=mocked_scan)),
            patch("backend.main.enrich_scan_violations", new=AsyncMock(return_value=([], {"provider": "local", "groq_findings": 0, "local_fallbacks": 0, "local_findings": 0}))),
            patch("backend.main.persist_report", new=AsyncMock(return_value=report_id)) as save_report,
            patch("backend.main.FRONTEND_ORIGIN", "https://a11ylens.embarko.app"),
        ):
            body = self.invoke_scan("198.51.100.15")

        saved_report = save_report.await_args.args[0]
        self.assertEqual(saved_report["url"], "https://example.com/library")
        self.assertTrue(body["saved"])
        self.assertEqual(body["share_path"], f"/r/{report_id}")
        self.assertEqual(body["share_url"], f"https://a11ylens.embarko.app/r/{report_id}")
        self.assertNotIn("secret", body["url"])

    def test_rejects_invalid_url_before_starting_browser(self) -> None:
        with (
            patch("backend.main.validate_public_url", side_effect=ValueError("Local host blocked.")),
            patch("backend.main.scan_with_playwright", new=AsyncMock()) as mocked_scan,
            patch("backend.main.enrich_scan_violations", new=AsyncMock()),
            self.assertRaises(HTTPException) as raised,
        ):
            self.invoke_scan("198.51.100.12", "http://localhost/")

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "Local host blocked.")
        mocked_scan.assert_not_awaited()

    def test_returns_safe_error_for_blocked_redirect(self) -> None:
        with (
            patch("backend.main.validate_public_url", return_value="https://example.com/"),
            patch(
                "backend.main.scan_with_playwright",
                new=AsyncMock(side_effect=main.ScanBlockedError("Redirect target is private.")),
            ),
            patch("backend.main.enrich_scan_violations", new=AsyncMock()),
            self.assertRaises(HTTPException) as raised,
        ):
            self.invoke_scan("198.51.100.13")

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "Redirect target is private.")

    def test_share_report_route_returns_stored_report(self) -> None:
        report_id = "b" * 32
        expected = {"id": report_id, "url": "https://example.com/", "score": {"score": 100}}
        previous_store = getattr(main.app.state, "report_store", None)
        main.app.state.report_store = SimpleNamespace(reports=object())
        try:
            with patch("backend.main.load_report", new=AsyncMock(return_value=expected)):
                report = run_immediate(main.get_report(report_id))
        finally:
            if previous_store is None:
                del main.app.state.report_store
            else:
                main.app.state.report_store = previous_store

        self.assertEqual(report, expected)

    def test_share_report_route_rejects_malformed_ids(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            run_immediate(main.get_report("short"))
        self.assertEqual(raised.exception.status_code, 404)

    def test_limits_requests_per_client(self) -> None:
        previous_limit = main.SCAN_RATE_LIMIT
        main.SCAN_RATE_LIMIT = 2
        try:
            with (
                patch("backend.main.validate_public_url", return_value="https://example.com/"),
                patch("backend.main.scan_with_playwright", new=AsyncMock(return_value={"violations": []})),
                patch("backend.main.enrich_scan_violations", new=AsyncMock(return_value=([], {"provider": "local", "groq_findings": 0, "local_fallbacks": 0, "local_findings": 0}))),
            ):
                self.invoke_scan("198.51.100.14")
                self.invoke_scan("198.51.100.14")
                with self.assertRaises(HTTPException) as raised:
                    self.invoke_scan("198.51.100.14")
        finally:
            main.SCAN_RATE_LIMIT = previous_limit

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers["Retry-After"], "60")


if __name__ == "__main__":
    unittest.main()
