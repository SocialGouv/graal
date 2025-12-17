import asyncio
import logging

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import command

logger = logging.getLogger(__name__)


class MigrationService:
    """
    Runs Alembic migrations at application startup with a PostgreSQL advisory lock
    to ensure concurrency-safe execution when multiple pods start simultaneously.
    """

    def __init__(self, database_url: str, lock_id: int = 1357911):
        # Convert to async driver format if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        # Remove unsupported sslmode parameters for asyncpg
        if "?sslmode=" in database_url:
            database_url = database_url.replace("?sslmode=require", "")
            database_url = database_url.replace("?sslmode=prefer", "")

        self.database_url = database_url
        self.lock_id = lock_id
        # Engine must be created lazily inside run_migrations(), not in the constructor
        self._engine: AsyncEngine | None = None

    def _get_alembic_config(self) -> Config:
        config = Config("alembic.ini")
        # Ensure migrations use the same database URL as the application
        config.set_main_option("sqlalchemy.url", self.database_url)
        return config

    async def _acquire_lock(self) -> None:
        assert self._engine is not None  # noqa: S101
        async with self._engine.connect() as conn:
            await conn.execute(
                text("SELECT pg_advisory_lock(:lock_id);"), {"lock_id": self.lock_id}
            )

    async def _release_lock(self) -> None:
        assert self._engine is not None  # noqa: S101
        async with self._engine.connect() as conn:
            await conn.execute(
                text("SELECT pg_advisory_unlock(:lock_id);"), {"lock_id": self.lock_id}
            )

    async def _run_alembic_upgrade(self) -> None:
        """
        Execute Alembic migrations in a thread executor to keep FastAPI async-safe.
        """
        loop = asyncio.get_running_loop()
        config = self._get_alembic_config()

        def sync_upgrade():
            command.upgrade(config, "head")

        await loop.run_in_executor(None, sync_upgrade)

    async def run_migrations(self) -> None:
        """
        Acquire advisory lock, run migrations, then release lock.
        """

        # Lazily initialize async engine (must bind to active running event loop)
        if self._engine is None:
            logger.info("Initializing async database engine for migrations...")
            self._engine = create_async_engine(self.database_url)

        lock_acquired = False
        try:
            logger.info(
                "Attempting to acquire PostgreSQL advisory lock for migrations..."
            )
            await self._acquire_lock()
            lock_acquired = True
            logger.info("Lock acquired. Running Alembic migrations...")
            await self._run_alembic_upgrade()
            logger.info("Alembic migrations completed successfully.")
        finally:
            if lock_acquired:
                logger.info("Releasing migration advisory lock.")
                await self._release_lock()
            if self._engine is not None:
                await self._engine.dispose()
                self._engine = None
