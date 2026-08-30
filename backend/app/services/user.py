from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    ServiceUnavailableError,
)
from app.core.security import hash_password, verify_password
from app.models.enums import AuditAction, AuditEntityType, UserRole
from app.models.rbac import Role
from app.models.user import User
from app.repositories import user as user_repository
from app.schemas.user import (
    PasswordChangeRequest,
    UserProfileUpdate,
    UserResponse,
)
from app.services import audit as audit_service


async def update_own_profile(
    session: AsyncSession,
    current_user: User,
    request: UserProfileUpdate,
) -> UserResponse:
    """Update only the authenticated User's editable profile fields."""

    try:
        email = str(request.email) if request.email is not None else None
        if email is not None and email != current_user.email:
            existing_user = await user_repository.get_other_user_by_email(
                session,
                email=email,
                current_user_id=current_user.id,
            )
            if existing_user is not None:
                raise ConflictError(
                    "An account with this email already exists."
                )

        role: Role | None = None
        role_changed = False
        if request.role is not None:
            if current_user.role.name == UserRole.ADMIN.value:
                raise ForbiddenError(
                    "Admin accounts cannot change their own role."
                )

            role = await user_repository.get_role_by_name(
                session,
                request.role.value,
            )
            if role is None:
                raise ServiceUnavailableError(
                    "Profile updates are temporarily unavailable."
                )
            role_changed = role.id != current_user.role_id

        user_repository.update_profile(
            current_user,
            name=request.name,
            email=email,
            role=role,
        )
        await user_repository.flush_user(session, current_user)
        await user_repository.refresh_user(session, current_user)

        if role_changed:
            audit_service.record_action(
                session,
                actor_id=current_user.id,
                action=AuditAction.USER_ROLE_CHANGED,
                entity_type=AuditEntityType.USER,
                entity_id=current_user.id,
            )

        response = UserResponse(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            role=(role.name if role is not None else current_user.role.name),
            is_active=current_user.is_active,
            created_at=current_user.created_at,
        )

        await session.commit()
        return response
    except IntegrityError as error:
        await session.rollback()
        if _get_constraint_name(error) == "uq_users_email":
            raise ConflictError(
                "An account with this email already exists."
            ) from error
        raise
    except Exception:
        await session.rollback()
        raise


async def change_own_password(
    session: AsyncSession,
    current_user: User,
    request: PasswordChangeRequest,
) -> None:
    """Replace the authenticated User's password and revoke refresh sessions."""

    try:
        current_password_is_valid = await run_in_threadpool(
            verify_password,
            request.current_password.get_secret_value(),
            current_user.password_hash,
        )
        if not current_password_is_valid:
            raise AuthenticationError("The current password is incorrect.")

        new_password_hash = await run_in_threadpool(
            hash_password,
            request.new_password.get_secret_value(),
        )
        user_repository.update_password_hash(
            current_user,
            new_password_hash,
        )
        await user_repository.revoke_active_refresh_tokens(
            session,
            user_id=current_user.id,
            revoked_at=datetime.now(timezone.utc),
        )
        await user_repository.flush_user(session, current_user)

        await session.commit()
    except Exception:
        await session.rollback()
        raise


def _get_constraint_name(error: IntegrityError) -> str | None:
    original_error = error.orig
    cause = getattr(original_error, "__cause__", None)
    diagnostics = getattr(original_error, "diag", None)

    return (
        getattr(original_error, "constraint_name", None)
        or getattr(cause, "constraint_name", None)
        or getattr(diagnostics, "constraint_name", None)
    )
