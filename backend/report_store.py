"""MongoDB persistence for public, unguessable scan report links."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any


class MongoReportStore:
    """A small async PyMongo adapter; one instance belongs to one API event loop."""

    def __init__(self, uri: str, database: str = "a11ylens", collection: str = "reports") -> None:
        self.uri = uri
        self.database_name = database
        self.collection_name = collection
        self.client: Any = None
        self.reports: Any = None

    async def connect(self) -> None:
        if not self.uri:
            return
        from pymongo import AsyncMongoClient

        self.client = AsyncMongoClient(
            self.uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            timeoutMS=10000,
            maxPoolSize=5,
        )
        await self.client.admin.command("ping")
        self.reports = self.client[self.database_name][self.collection_name]

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None
            self.reports = None

    async def save(self, report: dict[str, Any]) -> str | None:
        if self.reports is None:
            return None
        report_id = secrets.token_urlsafe(24)
        document = {
            **report,
            "_id": report_id,
            "created_at": datetime.now(timezone.utc),
        }
        await self.reports.insert_one(document)
        return report_id

    async def get(self, report_id: str) -> dict[str, Any] | None:
        if self.reports is None:
            return None
        document = await self.reports.find_one({"_id": report_id})
        if document is None:
            return None
        document["id"] = document.pop("_id")
        created_at = document.get("created_at")
        if isinstance(created_at, datetime):
            document["created_at"] = created_at.astimezone(timezone.utc).isoformat()
        return document
