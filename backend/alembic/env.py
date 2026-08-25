from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.database.model_registry import Base


config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ConfigParser treats percent signs as interpolation markers. Escaping them
# keeps percent-encoded credentials valid without storing the URL in the INI.
config.set_main_option(
    "sqlalchemy.url",
    settings.sqlalchemy_database_url.replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Configure an offline migration context without opening a connection."""

    context.configure(
        url=settings.sqlalchemy_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def configure_migration_context(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations with SQLAlchemy's async engine and asyncpg."""

    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(configure_migration_context)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
