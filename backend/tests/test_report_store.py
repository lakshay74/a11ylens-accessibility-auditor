"""Mocked Mongo adapter tests; no MongoDB service is required to run them."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from backend.report_store import MongoReportStore


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("A mocked Mongo operation unexpectedly yielded.")


class FakeCollection:
    def __init__(self):
        self.documents = {}

    async def insert_one(self, document: dict) -> None:
        self.documents[document["_id"]] = dict(document)

    async def find_one(self, query: dict) -> dict | None:
        document = self.documents.get(query["_id"])
        return dict(document) if document else None


class ReportStoreTests(unittest.TestCase):
    def test_saves_and_reads_report_with_random_share_id(self) -> None:
        store = MongoReportStore("mongodb://not-used")
        store.reports = FakeCollection()
        report = {"url": "https://example.com/", "score": {"score": 100}}

        report_id = run_immediate(store.save(report))
        restored = run_immediate(store.get(report_id))

        self.assertGreaterEqual(len(report_id), 30)
        self.assertEqual(restored["id"], report_id)
        self.assertEqual(restored["url"], report["url"])
        self.assertEqual(restored["score"], report["score"])
        self.assertTrue(restored["created_at"].endswith("+00:00"))

    def test_returns_none_when_mongo_is_not_configured(self) -> None:
        store = MongoReportStore("")
        self.assertIsNone(run_immediate(store.save({"url": "https://example.com/"})))
        self.assertIsNone(run_immediate(store.get("a" * 32)))


if __name__ == "__main__":
    unittest.main()
