from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def dispose_database_engine() -> None:
    await engine.dispose()
