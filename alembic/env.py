"""Alembic migration environment for GRAAL database.

This module configures Alembic to work with async SQLAlchemy and provides
database connection management for migrations.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models here so Alembic can detect them
# This is required for autogenerate to work
from graal.database.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from environment variables.

    Supports two formats:
    1. Single DATABASE_URL variable
    2. Split format (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSL_MODE)

    Returns:
        Database connection URL
    """
    # Try single DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Remove unsupported sslmode parameter for asyncpg
        if "?sslmode=" in database_url:
            database_url = database_url.replace("?sslmode=require", "")
            database_url = database_url.replace("?sslmode=prefer", "")
        return database_url

    # Construct from individual components
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "graal_dev")
    user = os.getenv("DB_USER", "graal_user")
    password = os.getenv("DB_PASSWORD", "graal_local_pass")

    # For local development, don't use SSL parameters (asyncpg doesn't support sslmode)
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection.

    Args:
        connection: SQLAlchemy connection to use for migrations
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async support.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get database URL and update config
    database_url = get_database_url()

    # Replace postgresql:// with postgresql+asyncpg:// for async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
