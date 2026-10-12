"""FastAPI dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import InvalidTokenError, decode_access_token
from app.db.database import get_db
from app.db.models import User
from app.services.answer_service import AnswerService
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService

_embeddings: EmbeddingService | None = None
_bearer = HTTPBearer(auto_error=False)


def get_embedding_service() -> EmbeddingService:
    """Return the process-wide embedding model wrapper."""
    global _embeddings
    if _embeddings is None:
        settings = get_settings()
        _embeddings = EmbeddingService(settings.embedding_model, settings.embedding_dimension)
    return _embeddings


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required.")
    settings = get_settings()
    try:
        user_id: UUID = decode_access_token(credentials.credentials, settings.jwt_secret)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc
    user = auth.get_user(user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired token.")
    return user


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
) -> DocumentService:
    settings = get_settings()
    return DocumentService(db, get_embedding_service(), settings)


def get_answer_service() -> AnswerService:
    return AnswerService(get_settings())


def get_search_service(
    db: Annotated[Session, Depends(get_db)],
) -> SearchService:
    settings = get_settings()
    return SearchService(db, get_embedding_service(), settings)
