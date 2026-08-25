from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Role
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def get_role_by_name(session: AsyncSession, name: str) -> Role | None:
    return await session.scalar(select(Role).where(Role.name == name))


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    statement = (
        select(User)
        .options(selectinload(User.role))
        .where(User.email == email)
    )
    return await session.scalar(statement)


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    statement = (
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )
    return await session.scalar(statement)


def add_user(
    session: AsyncSession,
    *,
    name: str,
    email: str,
    password_hash: str,
    role_id: UUID,
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        role_id=role_id,
    )
    session.add(user)
    return user


def add_refresh_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    return refresh_token


async def get_refresh_token_by_hash(
    session: AsyncSession,
    token_hash: str,
) -> RefreshToken | None:
    statement = (
        select(RefreshToken)
        .options(
            selectinload(RefreshToken.user).selectinload(User.role),
        )
        .where(RefreshToken.token_hash == token_hash)
    )
    return await session.scalar(statement)


async def get_refresh_token_for_update(
    session: AsyncSession,
    token_hash: str,
) -> RefreshToken | None:
    statement = (
        select(RefreshToken)
        .options(
            selectinload(RefreshToken.user).selectinload(User.role),
        )
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    return await session.scalar(statement)


def revoke_refresh_token(refresh_token: RefreshToken, revoked_at: datetime) -> None:
    refresh_token.revoked_at = revoked_at
