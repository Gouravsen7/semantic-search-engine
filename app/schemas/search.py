"""Search request and response models."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.config import MAX_TOP_K_CAP


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language query.",
        examples=["how does pgvector store embeddings"],
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=MAX_TOP_K_CAP,
        description="How many chunks to return. Omit this to use the server default.",
    )

    @field_validator("query")
    @classmethod
    def query_must_contain_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty.")
        return cleaned


class SearchResult(BaseModel):
    document_id: UUID
    filename: str
    content_type: str
    chunk_id: UUID
    chunk_index: int = Field(..., ge=0)
    content: str
    score: float = Field(..., description="Cosine similarity. Higher is more relevant.")


class SearchResponse(BaseModel):
    query: str
    interpreted_query: str
    category: str | None = None
    top_k: int
    answer: str
    results: list[SearchResult]
