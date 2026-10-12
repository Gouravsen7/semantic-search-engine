"""Semantic search."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_answer_service, get_current_user, get_search_service
from app.core.config import get_settings
from app.core.rate_limit import check_user_rate_limit
from app.db.models import User
from app.schemas.response import ApiResponse
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.answer_service import AnswerService
from app.services.query_understanding import understand_query
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "",
    response_model=ApiResponse[SearchResponse],
    summary="Search documents",
    description=(
        "Understands the query with Gemini, searches the matching document category when "
        "possible, then asks Gemini to answer in plain language using only the retrieved passages."
    ),
)
def search_documents(
    payload: SearchRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SearchService, Depends(get_search_service)],
    answers: Annotated[AnswerService, Depends(get_answer_service)],
) -> ApiResponse[SearchResponse]:
    settings = get_settings()
    check_user_rate_limit(user.id, "search", settings.search_rate_limit_per_minute)
    top_k = payload.top_k if payload.top_k is not None else service.settings.default_top_k
    understood = understand_query(payload.query, service.settings)
    if understood.routed:
        hits, category_used, _vector = service.search_with_category_fallback(
            user.id,
            understood.search_text,
            top_k,
            understood.category,
        )
    else:
        hits = service.search(user.id, payload.query, top_k)
        category_used = None
    answer = answers.answer(
        payload.query,
        [(hit.filename, hit.content) for hit in hits],
        category=category_used,
        interpreted_query=understood.search_text,
    )
    message = "No matching documents found." if not hits else "Search completed."
    return ApiResponse(message=message, data=SearchResponse(
        answer=answer,
        query=payload.query,
        interpreted_query=understood.search_text,
        category=category_used,
        top_k=top_k,
        results=[
            SearchResult(
                document_id=hit.document_id,
                filename=hit.filename,
                content_type=hit.content_type,
                chunk_id=hit.chunk_id,
                chunk_index=hit.chunk_index,
                content=hit.content,
                score=hit.score,
            )
            for hit in hits
        ],
    ))
