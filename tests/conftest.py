"""Shared test fixtures.

The API normally talks to MongoDB Atlas. For tests we swap the collection
out for a small in-memory fake so they run offline.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# make the project importable and give database.py something to load
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MONGO_URI", "mongodb://user:pass@localhost:27017")
os.environ.setdefault("DB_NAME", "obj_pipeline_test")
os.environ.setdefault("ROOT_USER", "root")
os.environ.setdefault("ROOT_PASS", "rootpass")


class FakeInsertResult:
    def __init__(self, inserted_id: str) -> None:
        self.inserted_id = inserted_id


class FakeUpdateResult:
    def __init__(self, matched_count: int) -> None:
        self.matched_count = matched_count


class FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self._documents = documents

    async def to_list(self, length: int) -> list[dict]:
        return self._documents[:length]


class FakeCollection:
    """Just enough of the Motor collection API for the routes to work."""

    def __init__(self) -> None:
        self.documents: list[dict] = []

    def _matches(self, document: dict, query: dict) -> bool:
        return all(document.get(key) == value for key, value in query.items())

    async def insert_one(self, document: dict) -> FakeInsertResult:
        document = dict(document)
        document.setdefault("_id", f"id{len(self.documents)}")
        self.documents.append(document)
        return FakeInsertResult(document["_id"])

    async def find_one(self, query: dict) -> dict | None:
        for document in self.documents:
            if self._matches(document, query):
                return document
        return None

    def find(self, query: dict | None = None) -> FakeCursor:
        if not query:
            return FakeCursor(list(self.documents))
        return FakeCursor([d for d in self.documents if self._matches(d, query)])

    async def update_one(self, query: dict, update: dict) -> FakeUpdateResult:
        for document in self.documents:
            if self._matches(document, query):
                document.update(update["$set"])
                return FakeUpdateResult(1)
        return FakeUpdateResult(0)

    async def delete_one(self, query: dict) -> None:
        self.documents = [d for d in self.documents if not self._matches(d, query)]


@pytest.fixture
def fake_collection(monkeypatch) -> FakeCollection:
    """Replace the real Atlas collection with the in-memory fake."""
    import routes

    collection = FakeCollection()
    monkeypatch.setattr(routes, "assets_collection", collection)
    return collection


@pytest.fixture
def client(fake_collection) -> TestClient:
    """A test client wired up to the fake collection."""
    from main import app

    return TestClient(app)
