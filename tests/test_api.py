"""HTTP contract tests. Document storage is in memory; extraction is real."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.deps import get_db, get_search_service
from app.core.config import get_settings
from app.main import app
from app.services.search_service import SearchHit


def test_openapi_lists_the_public_endpoints():
    schema = app.openapi()
    assert schema["info"]["title"] == "Semantic Search Engine"
    assert set(schema["paths"]) >= {
        "/health",
        "/auth/register",
        "/auth/login",
        "/auth/me",
        "/documents",
        "/documents/{document_id}",
        "/search",
    }
    assert schema["paths"]["/documents"]["post"]["summary"] == "Upload a document"
    assert schema["paths"]["/search"]["post"]["summary"] == "Search documents"


def test_upload_txt_list_get_and_delete(client, auth_headers):
    created = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("../../notes.txt", b"Semantic search stores vectors.", "text/plain")},
    )
    assert created.status_code == 201
    assert created.json()["message"] == "Document uploaded."
    assert created.json()["data"]["status"] == "ready"
    body = created.json()["data"]
    assert body["filename"] == "notes.txt"
    assert body["content_type"] == "text/plain"
    assert body["chunk_count"] == 1
    document_id = body["id"]

    listed = client.get("/documents", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["message"] == "Documents fetched."
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["documents"][0]["id"] == document_id

    detail = client.get(f"/documents/{document_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["message"] == "Document fetched."
    assert detail.json()["data"]["chunks"][0]["content"] == "Semantic search stores vectors."
    assert "embedding" not in detail.json()["data"]["chunks"][0]

    deleted = client.delete(f"/documents/{document_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Document deleted."
    assert client.get(f"/documents/{document_id}", headers=auth_headers).status_code == 404


def test_upload_pdf(client, auth_headers):
    import pymupdf

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "PDF body")
    payload = document.tobytes()
    document.close()

    response = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("guide.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["data"]["content_type"] == "application/pdf"
    assert response.json()["data"]["chunk_count"] == 1


def test_upload_rejects_unsupported_type(client, auth_headers):
    response = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("notes.md", b"hello", "text/markdown")},
    )
    assert response.status_code == 400
    assert "PDF and TXT" in response.json()["message"]


def test_upload_rejects_duplicate_bytes(client, auth_headers):
    payload = b"Duplicate content for testing."
    first = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("first.txt", payload, "text/plain")},
    )
    assert first.status_code == 201
    second = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("second.txt", payload, "text/plain")},
    )
    assert second.status_code == 409
    assert "already been uploaded" in second.json()["message"]


def test_upload_rejects_empty_and_blank_documents(client, auth_headers):
    empty = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 400

    blank = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("blank.txt", b" \n ", "text/plain")},
    )
    assert blank.status_code == 400
    assert "readable text" in blank.json()["message"]


def test_upload_rejects_files_over_the_size_limit(client, memory_service, auth_headers):
    memory_service.settings = memory_service.settings.model_copy(update={"max_upload_size_bytes": 4})
    response = client.post(
        "/documents",
        headers=auth_headers,
        files={"file": ("big.txt", b"12345", "text/plain")},
    )
    assert response.status_code == 400
    assert "maximum size" in response.json()["message"]


def test_upload_requires_a_file(client, auth_headers):
    assert client.post("/documents", headers=auth_headers).status_code == 422


def test_unknown_document_is_not_found(client, auth_headers):
    missing = client.get(f"/documents/{uuid4()}", headers=auth_headers)
    assert missing.status_code == 404
    assert "not found" in missing.json()["message"]


def test_invalid_document_id_is_rejected(client, auth_headers):
    assert client.get("/documents/not-a-uuid", headers=auth_headers).status_code == 422


def test_search_returns_ranked_chunks(client, auth_headers):
    hit = SearchHit(
        document_id=uuid4(),
        filename="pets.txt",
        content_type="text/plain",
        chunk_id=uuid4(),
        chunk_index=0,
        content="Cats and dogs live in the house.",
        score=0.82,
    )
    settings = get_settings()

    class StubSearch:
        def __init__(self) -> None:
            self.settings = settings
            self.calls = []

        def search(self, _user_id, query: str, top_k: int, **kwargs):
            self.calls.append((query, top_k))
            return [hit]

        def search_with_category_fallback(self, user_id, search_text, top_k, category):
            return self.search(user_id, search_text, top_k), None, []

    stub = StubSearch()
    app.dependency_overrides[get_search_service] = lambda: stub

    response = client.post(
        "/search",
        headers=auth_headers,
        json={"query": " household pets ", "top_k": 2},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Search completed."
    body = response.json()["data"]
    assert body["answer"]
    assert body["query"] == "household pets"
    assert body["interpreted_query"] == "household pets"
    assert body["category"] is None
    assert body["top_k"] == 2
    assert body["results"][0]["filename"] == "pets.txt"
    assert body["results"][0]["score"] == 0.82
    assert stub.calls == [("household pets", 2)]


def test_search_uses_the_default_top_k(client, auth_headers):
    class StubSearch:
        def __init__(self) -> None:
            self.settings = get_settings()
            self.top_k = None

        def search(self, _user_id, _query: str, top_k: int, **kwargs):
            self.top_k = top_k
            return []

        def search_with_category_fallback(self, user_id, search_text, top_k, category):
            return self.search(user_id, search_text, top_k), None, []

    stub = StubSearch()
    app.dependency_overrides[get_search_service] = lambda: stub
    response = client.post("/search", headers=auth_headers, json={"query": "embeddings"})
    assert response.status_code == 200
    assert response.json()["message"] == "No matching documents found."
    assert response.json()["data"]["answer"] == "Not found in your documents."
    assert response.json()["data"]["results"] == []
    assert stub.top_k == stub.settings.default_top_k


def test_search_rejects_blank_and_oversized_top_k(client, auth_headers):
    blank = client.post("/search", headers=auth_headers, json={"query": "   "})
    assert blank.status_code == 422
    assert blank.json()["message"] == "query: Query cannot be empty."
    assert client.post("/search", headers=auth_headers, json={"query": "cats", "top_k": 0}).status_code == 422
    assert client.post("/search", headers=auth_headers, json={"query": "cats", "top_k": 21}).status_code == 422


def test_health_ok_and_database_down():
    class HealthyDb:
        def execute(self, _statement):
            return None

    class BrokenDb:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, Exception("down"))

    def override(session):
        def _get_db():
            yield session

        return _get_db

    try:
        app.dependency_overrides[get_db] = override(HealthyDb())
        with TestClient(app) as test_client:
            assert test_client.get("/health").json() == {
                "message": "Service is healthy.",
                "data": {"status": "ok", "database": "ok"},
            }

        app.dependency_overrides[get_db] = override(BrokenDb())
        with TestClient(app) as test_client:
            response = test_client.get("/health")
            assert response.status_code == 503
            assert response.json()["message"] == "Database is unavailable."
    finally:
        app.dependency_overrides.clear()
