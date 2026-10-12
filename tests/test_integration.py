"""End-to-end test against PostgreSQL and the real embedding model.

Run it with the database from docker compose already up:

    INTEGRATION=1 pytest -m integration
"""

import os
import time
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration

if os.getenv("INTEGRATION") != "1":
    pytest.skip("Set INTEGRATION=1 to run database tests.", allow_module_level=True)

import pymupdf
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.main import app


@pytest.fixture(scope="module")
def integration_client():
    init_db()
    with TestClient(app) as client:
        yield client


def _headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password12"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _clear_documents(client: TestClient, headers: dict[str, str]) -> None:
    listed = client.get("/documents", headers=headers)
    assert listed.status_code == 200
    for document in listed.json()["data"]["documents"]:
        deleted = client.delete(f"/documents/{document['id']}", headers=headers)
        assert deleted.status_code == 200


def _pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def _until_ready(client: TestClient, headers: dict[str, str], document_id: str):
    deadline = time.time() + 180
    last = None
    while time.time() < deadline:
        last = client.get(f"/documents/{document_id}", headers=headers)
        assert last.status_code == 200
        status = last.json()["data"]["status"]
        if status == "ready":
            return last
        if status == "failed":
            raise AssertionError(last.json()["data"]["error_message"])
        time.sleep(0.5)
    raise AssertionError(last.text if last is not None else "document was not ready")


def test_upload_search_and_delete_round_trip(integration_client):
    health = integration_client.get("/health")
    assert health.status_code == 200
    assert health.json()["data"]["database"] == "ok"

    owner = _headers(integration_client, f"owner-{uuid4()}@example.com")
    other = _headers(integration_client, f"other-{uuid4()}@example.com")

    pets = integration_client.post(
        "/documents",
        headers=owner,
        files={
            "file": (
                "pets.txt",
                b"Cats and dogs are common household pets. A kitten likes to chase yarn.",
                "text/plain",
            )
        },
    )
    cooking = integration_client.post(
        "/documents",
        headers=owner,
        files={
            "file": (
                "cooking.pdf",
                _pdf("Bake bread with flour, water, salt, and yeast. Preheat the oven."),
                "application/pdf",
            )
        },
    )
    assert pets.status_code == 201
    assert cooking.status_code == 201
    assert pets.json()["data"]["status"] == "processing"
    assert cooking.json()["data"]["content_type"] == "application/pdf"
    ready_pets = _until_ready(integration_client, owner, pets.json()["data"]["id"])
    _until_ready(integration_client, owner, cooking.json()["data"]["id"])
    assert ready_pets.json()["data"]["chunk_count"] >= 1

    listed = integration_client.get("/documents", headers=owner)
    assert listed.json()["data"]["total"] == 2
    assert integration_client.get("/documents", headers=other).json()["data"]["total"] == 0

    hidden = integration_client.post(
        "/search",
        headers=other,
        json={"query": "household animals and kittens", "top_k": 2},
    )
    assert hidden.status_code == 200
    assert hidden.json()["data"]["results"] == []

    search = integration_client.post(
        "/search",
        headers=owner,
        json={"query": "household animals and kittens", "top_k": 2},
    )
    assert search.status_code == 200
    results = search.json()["data"]["results"]
    assert results
    assert results[0]["filename"] == "pets.txt"
    assert "kitten" in results[0]["content"].lower()
    if len(results) > 1:
        assert results[0]["score"] >= results[1]["score"]

    detail = integration_client.get(f"/documents/{pets.json()['data']['id']}", headers=owner)
    assert detail.status_code == 200
    assert detail.json()["data"]["chunks"]
    assert integration_client.get(f"/documents/{pets.json()['data']['id']}", headers=other).status_code == 404

    deleted = integration_client.delete(f"/documents/{pets.json()['data']['id']}", headers=owner)
    assert deleted.status_code == 200
    assert integration_client.get(f"/documents/{pets.json()['data']['id']}", headers=owner).status_code == 404
    _clear_documents(integration_client, owner)
