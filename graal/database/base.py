"""SQLAlchemy base configuration and engine setup.

This module provides the declarative base and async engine configuration
for the GRAAL database.
"""

import os
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Naming convention for constraints (helps with migrations)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all database models.

    All SQLAlchemy models should inherit from this class to be included
    in the metadata and migrations.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_database_url() -> str:
    """Get database URL from environment variables.

    Supports two formats:
    1. Single DATABASE_URL variable
    2. Split format (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSL_MODE)

    Returns:
        Database connection URL for async driver (postgresql+asyncpg://)
    """
    # Try single DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Replace postgresql:// with postgresql+asyncpg:// for async driver
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        # Remove unsupported parameters for asyncpg
        # asyncpg doesn't support sslmode, use ssl=true for SSL
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

    # For local development, don't use SSL
    # For production, set DATABASE_URL directly without sslmode
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


# Global async engine instance (created lazily)
_async_engine: AsyncEngine | None = None


def get_async_engine() -> AsyncEngine:
    """Get or create the async SQLAlchemy engine.

    This function returns a singleton async engine instance configured
    with connection pooling and appropriate settings.

    Returns:
        AsyncEngine instance
    """
    global _async_engine

    if _async_engine is None:
        database_url = get_database_url()

        _async_engine = create_async_engine(
            database_url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            pool_pre_ping=True,  # Verify connections before using
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_POOL_MAX_OVERFLOW", "10")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),  # 1 hour
        )

    return _async_engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get async session maker.

    Returns a configured session maker that creates AsyncSession instances
    bound to the async engine.

    Returns:
        async_sessionmaker configured for the application
    """
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI that provides async database sessions.

    This function is designed to be used with FastAPI's Depends() to inject
    database sessions into route handlers.

    Usage:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_async_session)):
            result = await session.execute(select(User))
            return result.scalars().all()

    Yields:
        AsyncSession instance
    """
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
