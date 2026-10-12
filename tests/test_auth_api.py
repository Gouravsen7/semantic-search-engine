"""Token login and per-user document access."""

from uuid import uuid4

from app.api.deps import get_search_service
from app.core.config import get_settings
from app.main import app
from app.services.search_service import SearchHit
from tests.memory import MemoryAuthService, MemoryDocumentService


def test_register_login_and_me(client):
    registered = client.post(
        "/auth/register",
        json={"email": "Owner@Example.com", "password": "password12"},
    )
    assert registered.status_code == 201
    assert registered.json()["message"] == "Account created."
    body = registered.json()["data"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "owner@example.com"
    assert "password" not in body["user"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["message"] == "User fetched."
    assert me.json()["data"]["id"] == body["user"]["id"]
    assert me.json()["data"]["email"] == "owner@example.com"

    logged_in = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "password12"},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["message"] == "Logged in."
    assert logged_in.json()["data"]["access_token"]


def test_register_rejects_a_duplicate_email_and_a_bad_login(client):
    payload = {"email": "owner@example.com", "password": "password12"}
    assert client.post("/auth/register", json=payload).status_code == 201
    duplicate = client.post("/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["message"] == "An account with this email already exists."

    wrong = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["message"] == "Invalid email or password."
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_user_sees_only_their_documents_and_search_hits(client):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")

    created = client.post(
        "/documents",
        headers=owner,
        files={"file": ("notes.txt", b"Only the owner should find this note.", "text/plain")},
    )
    assert created.status_code == 201
    document_id = created.json()["data"]["id"]

    empty = client.get("/documents", headers=other)
    assert empty.json()["message"] == "No documents found."
    assert empty.json()["data"]["total"] == 0
    assert client.get(f"/documents/{document_id}", headers=other).status_code == 404
    assert client.delete(f"/documents/{document_id}", headers=other).status_code == 404
    assert client.get("/documents", headers=owner).json()["data"]["total"] == 1

    hit = SearchHit(
        document_id=uuid4(),
        filename="notes.txt",
        content_type="text/plain",
        chunk_id=uuid4(),
        chunk_index=0,
        content="Only the owner should find this note.",
        score=0.9,
    )
    seen = []

    class ScopedSearch:
        def __init__(self) -> None:
            self.settings = get_settings()

        def search(self, user_id, query: str, top_k: int, **kwargs):
            seen.append(user_id)
            return [hit] if str(user_id) == _user_id(owner) else []

        def search_with_category_fallback(self, user_id, search_text, top_k, category):
            return self.search(user_id, search_text, top_k), None, []

    app.dependency_overrides[get_search_service] = lambda: ScopedSearch()
    own_search = client.post("/search", headers=owner, json={"query": "owner note"})
    other_search = client.post("/search", headers=other, json={"query": "owner note"})

    assert own_search.status_code == 200
    assert own_search.json()["message"] == "Search completed."
    assert own_search.json()["data"]["results"][0]["filename"] == "notes.txt"
    assert other_search.json()["message"] == "No matching documents found."
    assert other_search.json()["data"]["results"] == []
    assert seen[0] != seen[1]
    assert client.post("/documents", files={"file": ("notes.txt", b"hello", "text/plain")}).status_code == 401
    assert client.post("/search", json={"query": "notes"}).status_code == 401


def _register(client, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password12"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _user_id(headers: dict[str, str]) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    from app.core.security import decode_access_token

    return str(decode_access_token(token, get_settings().jwt_secret))
