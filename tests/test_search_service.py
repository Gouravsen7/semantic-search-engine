"""Search mapping and guards. SQL execution is stubbed."""

from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.core.exceptions import InvalidDocumentError
from app.services.search_service import SearchService


class FakeEmbeddings:
    def __init__(self) -> None:
        self.query: str | None = None

    def embed_query(self, query: str) -> list[float]:
        self.query = query
        return [0.2] * 384


class FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.executed = 0

    def execute(self, statement):
        self.statement = statement
        self.executed += 1
        return FakeResult(self.rows)


def test_search_maps_database_rows():
    chunk_id = uuid4()
    document_id = uuid4()
    session = FakeSession(
        [(chunk_id, document_id, 2, "cats meow", "pets.txt", "text/plain", 0.75)]
    )
    embeddings = FakeEmbeddings()
    service = SearchService(session, embeddings, get_settings())

    user_id = uuid4()
    hits = service.search(user_id, "household pets", top_k=3)

    assert session.executed == 1
    assert "user_id" in str(session.statement)
    assert "status" in str(session.statement)
    assert "category" not in str(session.statement)
    assert embeddings.query == "household pets"
    assert hits[0].chunk_id == chunk_id
    assert hits[0].document_id == document_id
    assert hits[0].chunk_index == 2
    assert hits[0].filename == "pets.txt"
    assert hits[0].score == 0.75


def test_search_rejects_blank_query_before_embedding():
    embeddings = FakeEmbeddings()
    service = SearchService(FakeSession([]), embeddings, get_settings())

    with pytest.raises(InvalidDocumentError, match="empty"):
        service.search(uuid4(), "   ", top_k=5)

    assert embeddings.query is None


def test_search_rejects_top_k_above_the_configured_maximum():
    service = SearchService(FakeSession([]), FakeEmbeddings(), get_settings())

    with pytest.raises(InvalidDocumentError, match="top_k"):
        service.search(uuid4(), "cats", top_k=get_settings().max_top_k + 1)


def test_search_applies_category_filter():
    chunk_id = uuid4()
    document_id = uuid4()
    session = FakeSession([(chunk_id, document_id, 0, "leave policy", "hr.pdf", "text/plain", 0.9)])
    service = SearchService(session, FakeEmbeddings(), get_settings())

    service.search(uuid4(), "leave days", top_k=3, category="HR")

    assert "category" in str(session.statement)


def test_search_drops_hits_below_min_search_score():
    chunk_id = uuid4()
    document_id = uuid4()
    session = FakeSession(
        [(chunk_id, document_id, 0, "weak", "other.pdf", "text/plain", 0.1)]
    )
    settings = get_settings().model_copy(update={"min_search_score": 0.25})
    service = SearchService(session, FakeEmbeddings(), settings)
    hits = service.search(uuid4(), "cats", top_k=3)
    assert hits == []


def test_category_fallback_searches_all_documents_when_scoped_score_is_low():
    chunk_id = uuid4()
    document_id = uuid4()
    low_row = [(chunk_id, document_id, 0, "weak match", "other.pdf", "text/plain", 0.1)]
    high_row = [(chunk_id, document_id, 0, "strong match", "policy.pdf", "text/plain", 0.9)]
    session = FakeSession([])
    session.rows_by_call = [low_row, high_row]
    session.call = 0

    def execute(statement):
        session.statement = statement
        session.executed += 1
        rows = session.rows_by_call[session.call]
        session.call += 1
        return FakeResult(rows)

    session.execute = execute  # type: ignore[method-assign]
    settings = get_settings().model_copy(update={"category_min_score": 0.35})
    service = SearchService(session, FakeEmbeddings(), settings)

    hits, category_used, _vector = service.search_with_category_fallback(
        uuid4(),
        "leave limit",
        top_k=3,
        category="HR",
    )

    assert category_used is None
    assert hits[0].content == "strong match"
    assert session.executed == 2
