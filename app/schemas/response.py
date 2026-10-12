"""Shared response shape for successful API calls."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    message: str
    data: T


class MessageResponse(BaseModel):
    message: str
