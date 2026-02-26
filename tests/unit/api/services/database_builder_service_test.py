"""Unit tests for DatabaseBuilderService database manifest creation.

These tests specifically cover the invariant that a newly created
SimilarityDBManifest can be committed together with its owner permission.

Regression: we previously observed FK violations when SQLAlchemy flushed
`amendment_database_permissions` before `similarity_db_manifests`.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from graal.api.services.database_builder_service import DatabaseBuilderService
from graal.database.base import Base, get_database_url
from graal.database.enums import DbRoleEnum
from graal.database.models import (
    AmendmentDatabasePermission,
    SimilarityDBManifest,
    User,
)


@pytest.fixture(autouse=True)
def mock_logging_config(mocker):
    """Avoid loading real logging.conf in tests."""

    mocker.patch("logging.config.fileConfig")


@pytest_asyncio.fixture()
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    # IMPORTANT: isolate test DB operations from the developer's environment.
    # These tests run destructive cleanup SQL (DELETE FROM users, etc.).
    # We therefore run everything inside a unique PostgreSQL schema.
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


class _DummyJobRegistry:
    def update_job(self, *_args, **_kwargs) -> None:
        return None


@pytest.mark.asyncio
async def test_create_new_manifest_creates_owner_permission(
    session_factory: async_sessionmaker[AsyncSession], mocker
):
    """Ensure we can commit manifest + permission without FK violations."""

    user = await _create_user(session_factory, suffix="db-builder")

    # Build a DatabaseBuilderService instance without calling its real __init__
    # (avoid requiring S3/builder deps). We only need _create_new_manifest.
    service: DatabaseBuilderService = DatabaseBuilderService.__new__(
        DatabaseBuilderService
    )
    service.job_registry = _DummyJobRegistry()
    service.s3_service = SimpleNamespace(similarity_db_folder="similarity_dbs")
    service.manifest_service = SimpleNamespace(
        _session_factory=session_factory,
        get_manifest_by_s3_path=mocker.AsyncMock(return_value=None),
    )

    # Avoid hitting S3 for metadata.
    service._get_s3_metadata = mocker.AsyncMock(
        return_value={"size": 123, "last_modified": datetime.now(timezone.utc)}
    )

    manifest_id = uuid.uuid4()

    await service._create_new_manifest(
        job_id="job-1",
        manifest_id=manifest_id,
        display_name="Test DB",
        s3_database_name="test-db__abcd",
        files_metadata=[],
        df=[1, 2, 3],  # only needs len(df)
        drop_empty_columns=[],
        similarity_threshold=0.9,
        eps=0.4,
        group_by_columns=[],
        config_file="configs/config.xlsx",
        user_id=user.id,
    )

    async with session_factory() as session:
        manifest = await session.get(SimilarityDBManifest, manifest_id)
        assert manifest is not None
        assert manifest.name == "Test DB"

        result = await session.execute(
            select(AmendmentDatabasePermission).where(
                AmendmentDatabasePermission.db_id == manifest_id,
                AmendmentDatabasePermission.user_id == user.id,
            )
        )
        perm = result.scalar_one_or_none()
        assert perm is not None
        assert perm.role == DbRoleEnum.owner
