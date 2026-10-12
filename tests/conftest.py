"""Shared API test setup."""

import os

os.environ["INIT_DB_ON_STARTUP"] = "false"
os.environ["GEMINI_API_KEY"] = ""
os.environ["ALLOW_INSECURE_JWT"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service, get_document_service
from app.core.config import get_settings
from app.main import app
from tests.memory import MemoryAuthService, MemoryDocumentService

get_settings.cache_clear()


@pytest.fixture
def memory_service() -> MemoryDocumentService:
    return MemoryDocumentService(get_settings())


@pytest.fixture
def client(memory_service: MemoryDocumentService):
    auth = MemoryAuthService()
    app.dependency_overrides[get_document_service] = lambda: memory_service
    app.dependency_overrides[get_auth_service] = lambda: auth
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "password12"},
    )
    assert response.status_code == 201
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
