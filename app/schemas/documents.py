"""Document request and response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkRead(BaseModel):
    id: UUID
    chunk_index: int = Field(..., ge=0)
    content: str


class DocumentRead(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int = Field(..., ge=0)
    chunk_count: int = Field(..., ge=0)
    status: str
    category: str | None = None
    error_message: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, document, chunk_count: int) -> "DocumentRead":
        return cls(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            chunk_count=chunk_count,
            status=document.status,
            category=document.category,
            error_message=document.error_message,
            created_at=document.created_at,
        )


class DocumentDetail(DocumentRead):
    chunks: list[ChunkRead]

    @classmethod
    def from_model(cls, document, chunks) -> "DocumentDetail":
        return cls(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            chunk_count=len(chunks),
            status=document.status,
            category=document.category,
            error_message=document.error_message,
            created_at=document.created_at,
            chunks=[
                ChunkRead(id=chunk.id, chunk_index=chunk.chunk_index, content=chunk.content)
                for chunk in chunks
            ],
        )


class DocumentListResponse(BaseModel):
    total: int = Field(..., ge=0)
    documents: list[DocumentRead]
