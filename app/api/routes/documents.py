"""Document upload and management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import get_current_user, get_document_service
from app.core.config import get_settings
from app.core.rate_limit import check_user_rate_limit
from app.db.models import User
from app.schemas.documents import DocumentDetail, DocumentListResponse, DocumentRead
from app.schemas.response import ApiResponse, MessageResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    response_model=ApiResponse[DocumentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description=(
        "Accepts one PDF or TXT file. The file is validated, text is extracted and "
        "split into chunks, and each chunk is stored with a 384-dimensional embedding. "
        "The upload returns while that work continues. Poll the document until status is ready. "
        "The original file bytes are not kept."
    ),
)
def upload_document(
    file: Annotated[UploadFile, File(description="A PDF or TXT file.")],
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiResponse[DocumentRead]:
    settings = get_settings()
    check_user_rate_limit(user.id, "upload", settings.upload_rate_limit_per_minute)
    max_size = service.settings.max_upload_size_bytes
    data = file.file.read(max_size + 1)
    document = service.create_document(user.id, file.filename or "", file.content_type, data)
    body = DocumentRead.from_model(document, chunk_count=len(document.chunks))
    message = "Document is processing." if document.status == "processing" else "Document uploaded."
    return ApiResponse(message=message, data=body)


@router.get(
    "",
    response_model=ApiResponse[DocumentListResponse],
    summary="List documents",
    description="Returns document metadata, newest first. Chunk text is not included.",
)
def list_documents(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiResponse[DocumentListResponse]:
    rows = service.list_documents(user.id)
    documents = [DocumentRead.from_model(document, chunk_count) for document, chunk_count in rows]
    message = "No documents found." if not documents else "Documents fetched."
    return ApiResponse(
        message=message,
        data=DocumentListResponse(total=len(documents), documents=documents),
    )


@router.get(
    "/{document_id}",
    response_model=ApiResponse[DocumentDetail],
    summary="Get a document",
    description="Returns document metadata and its text chunks. Embeddings are not included.",
)
def get_document(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ApiResponse[DocumentDetail]:
    document = service.get_document(user.id, document_id)
    chunks = service.list_chunks(user.id, document_id)
    return ApiResponse(message="Document fetched.", data=DocumentDetail.from_model(document, chunks))


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Delete a document",
    description="Deletes the document and every chunk that belongs to it.",
)
def delete_document(
    document_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> MessageResponse:
    service.delete_document(user.id, document_id)
    return MessageResponse(message="Document deleted.")
