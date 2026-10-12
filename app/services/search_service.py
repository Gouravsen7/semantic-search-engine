"""Natural-language search over stored chunks."""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import InvalidDocumentError
from app.db.models import Document, DocumentChunk
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchHit:
    document_id: UUID
    filename: str
    content_type: str
    chunk_id: UUID
    chunk_index: int
    content: str
    score: float


class SearchService:
    def __init__(self, db: Session, embeddings: EmbeddingService, settings: Settings) -> None:
        self.db = db
        self.embeddings = embeddings
        self.settings = settings

    def search(
        self,
        user_id: UUID,
        query: str,
        top_k: int,
        *,
        category: str | None = None,
        query_vector: list[float] | None = None,
    ) -> list[SearchHit]:
        cleaned = query.strip()
        if not cleaned:
            raise InvalidDocumentError("Search query cannot be empty.")
        if top_k < 1 or top_k > self.settings.max_top_k:
            raise InvalidDocumentError(f"top_k must be between 1 and {self.settings.max_top_k}.")

        vector = query_vector if query_vector is not None else self.embeddings.embed_query(cleaned)
        distance = DocumentChunk.embedding.cosine_distance(vector)
        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                Document.filename,
                Document.content_type,
                (1 - distance).label("score"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.user_id == user_id, Document.status == "ready")
        )
        if category is not None:
            statement = statement.where(Document.category == category)
        statement = statement.order_by(distance, DocumentChunk.id).limit(top_k)
        rows = self.db.execute(statement).all()
        hits = _filter_relevant([_to_hit(row) for row in rows], self.settings.min_search_score)
        logger.info(
            "Search returned %s hits for top_k=%s category=%s",
            len(hits),
            top_k,
            category,
        )
        return hits

    def search_with_category_fallback(
        self,
        user_id: UUID,
        search_text: str,
        top_k: int,
        category: str | None,
    ) -> tuple[list[SearchHit], str | None, list[float]]:
        """Search within category when useful; otherwise search all ready documents."""
        cleaned = search_text.strip()
        vector = self.embeddings.embed_query(cleaned)
        if category is not None:
            scoped = self.search(
                user_id,
                cleaned,
                top_k,
                category=category,
                query_vector=vector,
            )
            if scoped and scoped[0].score >= self.settings.category_min_score:
                return scoped, category, vector
        hits = self.search(user_id, cleaned, top_k, query_vector=vector)
        return hits, None, vector


def _filter_relevant(hits: list[SearchHit], min_score: float) -> list[SearchHit]:
    if not hits:
        return []
    if hits[0].score < min_score:
        return []
    return [h for h in hits if h.score >= min_score]


def _to_hit(row) -> SearchHit:
    chunk_id, document_id, chunk_index, content, filename, content_type, score = row
    return SearchHit(
        document_id=document_id,
        filename=filename,
        content_type=content_type,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        content=content,
        score=float(score),
    )
