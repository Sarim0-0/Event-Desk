from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Role
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def list_all_users(session: AsyncSession) -> list[User]:
    """Load every User and their Role in deterministic newest-first order."""

    statement = (
        select(User)
        .options(selectinload(User.role))
        .order_by(User.created_at.desc(), User.id.desc())
    )
    users = await session.scalars(statement)
    return list(users.all())


async def get_user_by_id(
    session: AsyncSession,
    user_id: UUID,
) -> User | None:
    """Load a target User and their current Role."""

    statement = (
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )
    return await session.scalar(statement)


async def get_other_user_by_email(
    session: AsyncSession,
    *,
    email: str,
    current_user_id: UUID,
) -> User | None:
    """Find an account using the email, excluding the current User."""

    statement = select(User).where(
        User.email == email,
        User.id != current_user_id,
    )
    return await session.scalar(statement)


async def get_role_by_name(
    session: AsyncSession,
    role_name: str,
) -> Role | None:
    return await session.scalar(select(Role).where(Role.name == role_name))


def update_profile(
    user: User,
    *,
    name: str | None = None,
    email: str | None = None,
    role: Role | None = None,
) -> User:
    """Apply only the profile fields supported by self-service updates."""

    if name is not None:
        user.name = name
    if email is not None:
        user.email = email
    if role is not None:
        user.role = role

    return user


def update_password_hash(user: User, password_hash: str) -> None:
    user.password_hash = password_hash


def update_user_role(user: User, role: Role) -> User:
    user.role = role
    return user


def deactivate_user(user: User, deactivated_at: datetime) -> User:
    """Mark the supplied User inactive without deleting their row."""

    user.is_active = False
    user.deleted_at = deactivated_at
    return user


async def revoke_active_refresh_tokens(
    session: AsyncSession,
    *,
    user_id: UUID,
    revoked_at: datetime,
) -> None:
    statement = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > revoked_at,
        )
        .values(revoked_at=revoked_at)
    )
    await session.execute(statement)


async def refresh_user(session: AsyncSession, user: User) -> User:
    await session.refresh(
        user,
        attribute_names=[
            "id",
            "name",
            "email",
            "role_id",
            "is_active",
            "deleted_at",
            "created_at",
            "updated_at",
        ],
    )
    return user
