from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    SignUpRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth import (
    AccountUnavailableError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RegistrationRoleUnavailableError,
    log_in,
    log_out,
    refresh_access_token,
    sign_up,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_endpoint(
    request: SignUpRequest,
    session: DatabaseSession,
) -> UserResponse:
    try:
        return await sign_up(session, request)
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error
    except RegistrationRoleUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable.",
        ) from error


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    request: LoginRequest,
    session: DatabaseSession,
) -> TokenResponse:
    try:
        return await log_in(session, request)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_endpoint(
    request: RefreshTokenRequest,
    session: DatabaseSession,
) -> AccessTokenResponse:
    try:
        return await refresh_access_token(session, request)
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AccountUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        ) from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    request: RefreshTokenRequest,
    session: DatabaseSession,
) -> Response:
    try:
        await log_out(session, request)
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
