from datetime import datetime, timezone

from jwt.exceptions import InvalidTokenError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    ServiceUnavailableError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_subject,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories import auth as auth_repository
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    SignUpRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse


async def sign_up(
    session: AsyncSession,
    request: SignUpRequest,
) -> UserResponse:
    raw_password = request.password.get_secret_value()
    password_hash = await run_in_threadpool(hash_password, raw_password)

    try:
        async with session.begin():
            email = str(request.email)
            if await auth_repository.get_user_by_email(session, email) is not None:
                raise ConflictError(
                    "An account with this email already exists."
                )

            role = await auth_repository.get_role_by_name(
                session,
                request.role.value,
            )
            if role is None:
                raise ServiceUnavailableError(
                    "Registration is temporarily unavailable."
                )

            user = auth_repository.add_user(
                session,
                name=request.name,
                email=email,
                password_hash=password_hash,
                role_id=role.id,
            )
            await session.flush()
            await session.refresh(user)

            response = UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=role.name,
                is_active=user.is_active,
                created_at=user.created_at,
            )
    except IntegrityError as error:
        raise ConflictError(
            "An account with this email already exists."
        ) from error

    return response


async def log_in(
    session: AsyncSession,
    request: LoginRequest,
) -> TokenResponse:
    async with session.begin():
        user = await auth_repository.get_user_by_email(
            session,
            str(request.email),
        )
        if user is None:
            raise AuthenticationError("Incorrect email or password.")

        password_is_valid = await run_in_threadpool(
            verify_password,
            request.password.get_secret_value(),
            user.password_hash,
        )
        if not password_is_valid:
            raise AuthenticationError("Incorrect email or password.")

        _ensure_account_is_available(user)
        return await _issue_token_pair(session, user)


async def refresh_access_token(
    session: AsyncSession,
    request: RefreshTokenRequest,
) -> AccessTokenResponse:
    try:
        user_id = decode_token_subject(request.refresh_token, "refresh")
    except InvalidTokenError as error:
        raise AuthenticationError(
            "Invalid or expired refresh token."
        ) from error

    token_hash = hash_refresh_token(request.refresh_token)
    now = datetime.now(timezone.utc)

    async with session.begin():
        stored_token = await auth_repository.get_refresh_token_by_hash(
            session,
            token_hash,
        )
        if (
            stored_token is None
            or stored_token.user_id != user_id
            or stored_token.revoked_at is not None
            or stored_token.expires_at <= now
        ):
            raise AuthenticationError("Invalid or expired refresh token.")

        _ensure_account_is_available(stored_token.user)
        return AccessTokenResponse(
            access_token=create_access_token(
                stored_token.user.id,
                stored_token.user.role.name,
            )
        )


async def log_out(
    session: AsyncSession,
    request: RefreshTokenRequest,
) -> None:
    try:
        user_id = decode_token_subject(request.refresh_token, "refresh")
    except InvalidTokenError as error:
        raise AuthenticationError("Invalid refresh token.") from error

    token_hash = hash_refresh_token(request.refresh_token)

    async with session.begin():
        stored_token = await auth_repository.get_refresh_token_for_update(
            session,
            token_hash,
        )
        if stored_token is None or stored_token.user_id != user_id:
            raise AuthenticationError("Invalid refresh token.")

        if stored_token.revoked_at is None:
            auth_repository.revoke_refresh_token(
                stored_token,
                datetime.now(timezone.utc),
            )


async def get_authenticated_user(
    session: AsyncSession,
    access_token: str,
) -> User:
    try:
        user_id = decode_token_subject(access_token, "access")
    except InvalidTokenError as error:
        raise AuthenticationError(
            "Could not validate credentials."
        ) from error

    user = await auth_repository.get_user_by_id(session, user_id)
    if user is None:
        raise AuthenticationError("Could not validate credentials.")

    _ensure_account_is_available(user)
    return user


async def _issue_token_pair(
    session: AsyncSession,
    user: User,
) -> TokenResponse:
    access_token = create_access_token(user.id, user.role.name)
    refresh_token, refresh_expires_at = create_refresh_token(user.id)

    auth_repository.add_refresh_token(
        session,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=refresh_expires_at,
    )
    await session.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def _ensure_account_is_available(user: User) -> None:
    if not user.is_active or user.deleted_at is not None:
        raise ForbiddenError("Account is inactive.")
