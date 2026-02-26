"""Unit tests for SimilarityDBManifestService."""

import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from graal.api.services.similarity_db_manifest_service import (
    SimilarityDBManifestService,
)
from graal.database.base import Base, get_database_url
from graal.database.models import SimilarityDBManifest, User


class _DummyDatabaseService:
    def __init__(self) -> None:
        self.delete_database_file = AsyncMock()


class _DummyS3Service:
    def __init__(self) -> None:
        self.similarity_db_folder = "similarity_dbs"
        self.database = _DummyDatabaseService()


@pytest_asyncio.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    # IMPORTANT: isolate test DB operations from the developer's environment.
    # This test suite truncates core tables (users, manifests...).
    schema_name = f"test_{uuid.uuid4().hex}"

    engine = create_async_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": schema_name}},
    )
    tables = [
        Base.metadata.tables["amendment_database_permissions"],
        Base.metadata.tables["similarity_db_manifests"],
        Base.metadata.tables["users"],
    ]

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(bind=sync_conn, tables=tables)
        )
        # Clean tables between tests (respect FK ordering)
        await conn.execute(text("DELETE FROM amendment_database_permissions"))
        await conn.execute(text("DELETE FROM similarity_db_manifests"))
        await conn.execute(text("DELETE FROM users"))

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await engine.dispose()


@pytest.fixture()
def s3_service() -> _DummyS3Service:
    return _DummyS3Service()


async def _create_user(
    session_factory: async_sessionmaker[AsyncSession], *, suffix: str
) -> User:
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            proconnect_sub=f"sub-{suffix}",
            email=f"user-{suffix}@example.com",
            email_verified=True,
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_manifest(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    *,
    suffix: str,
) -> SimilarityDBManifest:
    async with session_factory() as session:
        manifest = SimilarityDBManifest(
            created_by_user_id=user_id,
            name=f"Test DB {suffix}",
            s3_folder_path="similarity_dbs/project",
            s3_file_path=f"similarity_dbs/project/{suffix}.parquet",
            size_bytes=1024,
            row_count=10,
            last_modified=datetime.now(timezone.utc),
            db_metadata={"project": "project"},
            input_files=None,
            is_active=True,
        )
        session.add(manifest)
        await session.commit()
        await session.refresh(manifest)
        return manifest


@pytest.mark.asyncio
async def test_delete_manifest_removes_db_and_file(
    session_factory: async_sessionmaker[AsyncSession],
    s3_service: _DummyS3Service,
):
    service = SimilarityDBManifestService(session_factory, s3_service)
    user = await _create_user(session_factory, suffix="db-one-user")
    manifest = await _create_manifest(session_factory, user.id, suffix="db-one")

    result = await service.delete_database_by_id(manifest.id)

    assert result.id == manifest.id
    s3_service.database.delete_database_file.assert_awaited_once_with("project/db-one")

    async with session_factory() as session:
        assert await session.get(SimilarityDBManifest, manifest.id) is None


@pytest.mark.asyncio
async def test_delete_manifest_warns_when_s3_file_missing(
    session_factory: async_sessionmaker[AsyncSession],
    s3_service: _DummyS3Service,
    caplog: pytest.LogCaptureFixture,
):
    service = SimilarityDBManifestService(session_factory, s3_service)
    user = await _create_user(session_factory, suffix="db-missing-user")
    manifest = await _create_manifest(session_factory, user.id, suffix="db-missing")

    caplog.set_level(logging.WARNING)
    s3_service.database.delete_database_file.side_effect = FileNotFoundError("nope")

    await service.delete_database_by_id(manifest.id)

    assert "S3 database file missing" in caplog.text

    async with session_factory() as session:
        assert await session.get(SimilarityDBManifest, manifest.id) is None
