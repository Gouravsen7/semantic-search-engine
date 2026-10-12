"""Document persistence without a database connection."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.exceptions import ConflictError, DocumentNotFoundError
from app.db.models import Document
from app.services.content_hash import sha256_hex
from app.services.document_service import DocumentService


class FakeEmbeddings:
    def __init__(self) -> None:
        self.texts: list[str] | None = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.texts = list(texts)
        return [[0.1] * 384 for _ in texts]


class FakeScalars:
    def __init__(self, value) -> None:
        self._value = value

    def first(self):
        return self._value


class FakeSession:
    def __init__(self, duplicate=None) -> None:
        self.added = []
        self.committed = False
        self.refreshed = False
        self.rolled_back = False
        self.duplicate = duplicate

    def add(self, obj) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, _obj) -> None:
        self.refreshed = True

    def get(self, _model, obj_id):
        for obj in self.added:
            if obj.id == obj_id:
                return obj
        return None

    def delete(self, obj) -> None:
        self.added.remove(obj)

    def scalars(self, _statement):
        return FakeScalars(self.duplicate)

    def execute(self, _statement):
        class _Result:
            def all(self_inner):
                return []

        return _Result()


def _service(session=None, embeddings=None, start_job=lambda *_args: None, **setting_overrides):
    settings = get_settings().model_copy(update=setting_overrides)
    return DocumentService(
        session or FakeSession(),
        embeddings or FakeEmbeddings(),
        settings,
        start_job=start_job,
    )


def test_create_document_stores_embeddings_and_chunk_indexes():
    session = FakeSession()
    embeddings = FakeEmbeddings()
    service = _service(
        session,
        embeddings,
        chunk_size=12,
        chunk_overlap=5,
    )
    user_id = uuid4()
    payload = b"alpha beta gamma delta epsilon zeta"
    document = service.create_document(
        user_id,
        "folder/pets.txt",
        "text/plain",
        payload,
    )
    assert document.status == "processing"
    assert list(document.chunks) == []

    service.finish(document, payload)

    assert document.status == "ready"
    assert document.user_id == user_id
    assert document.filename == "pets.txt"
    assert document.content_type == "text/plain"
    assert [chunk.chunk_index for chunk in document.chunks] == [0, 1, 2, 3]
    assert document.chunks[0].content == "alpha beta"
    assert len(document.chunks[0].embedding) == 384
    assert embeddings.texts == [chunk.content for chunk in document.chunks]
    assert session.committed is True
    assert session.refreshed is True


def test_unreadable_text_is_stored_as_failed():
    session = FakeSession()
    service = _service(session)
    document = service.create_document(uuid4(), "blank.txt", "text/plain", b" \n ")

    service.finish(document, b" \n ")

    failed = session.get(type(document), document.id)
    assert failed.status == "failed"
    assert "readable text" in failed.error_message


def test_delete_document_removes_the_stored_row():
    session = FakeSession()
    service = _service(session)
    user_id = uuid4()
    document = service.create_document(user_id, "notes.txt", "text/plain", b"hello there")

    service.delete_document(user_id, document.id)

    assert session.added == []
    with pytest.raises(DocumentNotFoundError):
        service.get_document(user_id, document.id)


def test_missing_document_raises_not_found():
    service = _service()
    with pytest.raises(DocumentNotFoundError):
        service.get_document(uuid4(), uuid4())


def test_duplicate_upload_is_rejected():
    payload = b"same bytes for duplicate check"
    duplicate = Document(
        id=uuid4(),
        user_id=uuid4(),
        filename="policy.txt",
        content_type="text/plain",
        content_hash=sha256_hex(payload),
        size_bytes=len(payload),
        status="ready",
    )
    session = FakeSession(duplicate=duplicate)
    service = _service(session)
    with pytest.raises(ConflictError, match="policy.txt"):
        service.create_document(duplicate.user_id, "copy.txt", "text/plain", payload)
    assert session.added == []


def test_database_failure_rolls_back():
    class BoomSession(FakeSession):
        def commit(self) -> None:
            raise SQLAlchemyError("database unavailable")

    session = BoomSession()
    service = _service(session)
    with pytest.raises(SQLAlchemyError):
        service.create_document(uuid4(), "notes.txt", "text/plain", b"hello there")
    assert session.rolled_back is True
