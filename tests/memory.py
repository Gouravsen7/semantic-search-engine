"""In-memory stand-ins used by API tests."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import ConflictError, DocumentNotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.services.content_hash import sha256_hex
from app.services.document_processor import process_document
from app.services.document_categories import GENERAL


class MemoryAuthService:
    """Stores users in a dict and uses the real password hash."""

    def __init__(self) -> None:
        self.users: dict = {}

    def register(self, email: str, password: str):
        if self._by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")
        user = _User(
            id=uuid4(),
            email=email,
            password_hash=hash_password(password),
            created_at=datetime.now(timezone.utc),
        )
        self.users[user.id] = user
        return user

    def authenticate(self, email: str, password: str):
        user = self._by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")
        return user

    def get_user(self, user_id):
        return self.users.get(user_id)

    def _by_email(self, email: str):
        for user in self.users.values():
            if user.email == email:
                return user
        return None


class MemoryDocumentService:
    """Runs the real upload pipeline and keeps the result in a dict."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.documents: dict = {}
        self._clock = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def create_document(self, user_id, filename: str, content_type: str | None, data: bytes):
        content_hash = sha256_hex(data)
        for document in self.documents.values():
            if (
                document.user_id == user_id
                and document.content_hash == content_hash
                and document.status in ("processing", "ready")
            ):
                raise ConflictError(f"This document has already been uploaded as {document.filename}.")

        processed = process_document(
            filename,
            content_type,
            data,
            max_size=self.settings.max_upload_size_bytes,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        self._clock += timedelta(seconds=1)
        document_id = uuid4()
        chunks = [
            _Chunk(id=uuid4(), chunk_index=index, content=content)
            for index, content in enumerate(processed.chunks)
        ]
        document = _Document(
            id=document_id,
            user_id=user_id,
            filename=processed.filename,
            content_type=processed.content_type,
            content_hash=content_hash,
            category=GENERAL,
            size_bytes=len(data),
            status="ready",
            error_message=None,
            created_at=self._clock,
            chunks=chunks,
        )
        self.documents[document_id] = document
        return document

    def list_documents(self, user_id):
        documents = [
            document for document in self.documents.values() if document.user_id == user_id
        ]
        documents.sort(key=lambda item: item.created_at, reverse=True)
        return [(document, len(document.chunks)) for document in documents]

    def get_document(self, user_id, document_id):
        document = self.documents.get(document_id)
        if document is None or document.user_id != user_id:
            raise DocumentNotFoundError(document_id)
        return document

    def list_chunks(self, user_id, document_id):
        return list(self.get_document(user_id, document_id).chunks)

    def delete_document(self, user_id, document_id):
        self.get_document(user_id, document_id)
        del self.documents[document_id]


class _User:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class _Document:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class _Chunk:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)
