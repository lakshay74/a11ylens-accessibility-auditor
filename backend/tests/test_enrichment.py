"""Prompt output validation and local fallback tests for scan explanations."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend import main


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("A mocked explanation operation unexpectedly yielded.")


class FakeResponse:
    def __init__(self, content: dict):
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.content


class FakeAsyncClient:
    response: FakeResponse
    payload: dict | None = None

    def __init__(self, *args, **kwargs):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, _url: str, *, headers: dict, json: dict):
        self.payload = json
        return self.response


class EnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.criteria = [{"id": "1.1.1", "title": "Non-text Content", "summary": "Provide text alternatives."}]
        self.violation = {
            "id": "image-alt",
            "impact": "critical",
            "description": "Images must have alternate text",
            "nodes": [{"target": ["img"], "html": "<img src='x'>", "failureSummary": "Add alt text."}],
            "totalNodes": 1,
        }

    def test_groq_response_is_limited_to_known_finding_and_criteria_ids(self) -> None:
        response_item = {
            "id": "image-alt",
            "explanation": "This image has no text alternative.",
            "why_it_matters": "Screen readers cannot describe it.",
            "who_it_affects": "People using screen readers.",
            "recommendation": "Add an accurate alt attribute.",
            "fixed_html": "<img src='x' alt='Description'>",
            "criteria": ["1.1.1", "9.9.9"],
        }
        FakeAsyncClient.response = FakeResponse({
            "choices": [{"message": {"content": json.dumps({"findings": [response_item, {**response_item, "id": "invented"}]})}}]
        })
        source = {
            "id": "image-alt",
            "criteria": self.criteria,
            "retrieval": {"method": "TF-IDF", "count": 1},
        }
        with (
            patch("backend.main.GROQ_API_KEY", "test-key"),
            patch("backend.main.httpx.AsyncClient", FakeAsyncClient),
        ):
            result = run_immediate(main.generate_scan_explanations([source]))

        self.assertEqual(set(result), {"image-alt"})
        self.assertEqual(result["image-alt"]["criteria"], self.criteria)
        self.assertEqual(result["image-alt"]["who_it_affects"], "People using screen readers.")

    def test_scan_falls_back_to_local_guidance_when_groq_fails(self) -> None:
        retrieval = SimpleNamespace(criteria=tuple(self.criteria), method="TF-IDF")
        with (
            patch("backend.main.GROQ_API_KEY", "test-key"),
            patch("backend.main.retrieve_criteria", return_value=retrieval),
            patch("backend.main.generate_scan_explanations", new=AsyncMock(side_effect=RuntimeError("provider down"))),
        ):
            enriched, summary = run_immediate(main.enrich_scan_violations([self.violation]))

        self.assertEqual(enriched[0]["id"], "image-alt")
        self.assertEqual(enriched[0]["offending_html"], "<img src='x'>")
        self.assertEqual(enriched[0]["insight"]["mode"], "local_fallback")
        self.assertEqual(enriched[0]["insight"]["criteria"], self.criteria)
        self.assertEqual(enriched[0]["insight"]["fixed_html"], "")
        self.assertEqual(summary["local_fallbacks"], 1)

    def test_local_mode_still_attaches_structured_audience_and_axe_html(self) -> None:
        retrieval = SimpleNamespace(criteria=tuple(self.criteria), method="TF-IDF")
        with (
            patch("backend.main.GROQ_API_KEY", ""),
            patch("backend.main.retrieve_criteria", return_value=retrieval),
        ):
            enriched, summary = run_immediate(main.enrich_scan_violations([self.violation]))

        self.assertEqual(enriched[0]["insight"]["mode"], "local")
        self.assertIn("screen reader", enriched[0]["insight"]["who_it_affects"])
        self.assertEqual(enriched[0]["offending_html"], "<img src='x'>")
        self.assertEqual(summary["provider"], "local")


if __name__ == "__main__":
    unittest.main()
