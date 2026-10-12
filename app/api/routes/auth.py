"""Account registration and token login."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_auth_service, get_current_user
from app.core.config import get_settings
from app.core.rate_limit import check_auth_rate_limit
from app.core.security import create_access_token
from app.db.models import User
from app.schemas.auth import Credentials, TokenResponse, UserRead
from app.schemas.response import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description="Creates a user and returns a bearer token. Email is stored in lowercase.",
)
def register(
    request: Request,
    payload: Credentials,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenResponse]:
    check_auth_rate_limit(request, get_settings())
    user = service.register(payload.email, payload.password)
    return ApiResponse(message="Account created.", data=_token_response(user))


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Log in",
    description="Checks the email and password and returns a bearer token.",
)
def login(
    request: Request,
    payload: Credentials,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenResponse]:
    check_auth_rate_limit(request, get_settings())
    user = service.authenticate(payload.email, payload.password)
    return ApiResponse(message="Logged in.", data=_token_response(user))


@router.get(
    "/me",
    response_model=ApiResponse[UserRead],
    summary="Current user",
    description="Returns the user for the bearer token.",
)
def me(user: Annotated[User, Depends(get_current_user)]) -> ApiResponse[UserRead]:
    return ApiResponse(message="User fetched.", data=UserRead.model_validate(user))


def _token_response(user) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user.id, settings.jwt_secret, settings.jwt_expire_minutes),
        token_type="bearer",
        user=UserRead.model_validate(user),
    )
