"""Unit tests for OAuthStateService."""

import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from graal.api.services.oauth_state_service import OAuthStateService
from graal.database.base import Base, get_database_url
from graal.database.models import OAuthAuthRequest


@pytest_asyncio.fixture()
async def session_factory():
    # IMPORTANT: isolate test DB operations from the developer's environment.
    # This suite deletes OAuth request rows during setup.
    schema_name = f"test_{uuid.uuid4().hex}"

    engine = create_async_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": schema_name}},
    )
    oauth_requests_table = Base.metadata.tables[OAuthAuthRequest.__tablename__]
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn, tables=[oauth_requests_table]
            )
        )
        # Use SQLAlchemy delete for portability and to avoid schema/FK issues
        await conn.execute(text("DELETE FROM oauth_auth_requests"))

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_consume_state(
    session_factory: async_sessionmaker[AsyncSession],
):
    service = OAuthStateService(session_factory)

    state = "state-123"
    code_verifier = "verifier-abc"

    stored = await service.create_state(state, code_verifier)
    assert stored.state == state
    assert stored.code_verifier == code_verifier

    consumed = await service.consume_state(state, max_age_seconds=600)
    assert consumed is not None
    assert consumed.code_verifier == code_verifier

    # Second consume should return None (already deleted)
    consumed_again = await service.consume_state(state, max_age_seconds=600)
    assert consumed_again is None


@pytest.mark.asyncio
async def test_state_expiration(session_factory: async_sessionmaker[AsyncSession]):
    service = OAuthStateService(session_factory)
    state = "state-expired"

    stored = await service.create_state(state, "code")

    # Directly update created_at to simulate old state
    async with session_factory() as session:
        db_obj = await session.get(OAuthAuthRequest, stored.id)
        assert db_obj is not None
        db_obj.created_at = db_obj.created_at - timedelta(minutes=20)
        await session.commit()

    consumed = await service.consume_state(state, max_age_seconds=600)
    assert consumed is None


@pytest.mark.asyncio
async def test_consume_missing_state(session_factory: async_sessionmaker[AsyncSession]):
    service = OAuthStateService(session_factory)

    consumed = await service.consume_state("missing", max_age_seconds=600)
    assert consumed is None
