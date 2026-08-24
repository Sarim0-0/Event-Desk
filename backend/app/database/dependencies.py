from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide one async database session for a request."""

    async with async_session_factory() as session:
        yield session
