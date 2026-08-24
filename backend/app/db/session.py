from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.sqlalchemy_database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout_seconds,
    pool_recycle=settings.database_pool_recycle_seconds,
    connect_args={
        "command_timeout": settings.database_command_timeout_seconds,
        "server_settings": {
            "application_name": settings.database_application_name,
        },
    },
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def dispose_database_engine() -> None:
    """Close all pooled connections during application shutdown."""

    await engine.dispose()
