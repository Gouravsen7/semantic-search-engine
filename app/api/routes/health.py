"""Liveness and database connectivity."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.response import ApiResponse

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    database: str = Field(examples=["ok"])


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="Health check",
    description="Returns ok when the API can run a query against PostgreSQL.",
)
def health(db: Annotated[Session, Depends(get_db)]) -> ApiResponse[HealthResponse]:
    db.execute(text("SELECT 1"))
    return ApiResponse(message="Service is healthy.", data=HealthResponse(status="ok", database="ok"))
