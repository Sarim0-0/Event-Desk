from fastapi import APIRouter, Response, status

from app.api.dependencies import DatabaseSession
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    SignUpRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth import log_in, log_out, refresh_access_token, sign_up


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_endpoint(
    request: SignUpRequest,
    session: DatabaseSession,
) -> UserResponse:
    return await sign_up(session, request)


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    request: LoginRequest,
    session: DatabaseSession,
) -> TokenResponse:
    return await log_in(session, request)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_endpoint(
    request: RefreshTokenRequest,
    session: DatabaseSession,
) -> AccessTokenResponse:
    return await refresh_access_token(session, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    request: RefreshTokenRequest,
    session: DatabaseSession,
) -> Response:
    await log_out(session, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
