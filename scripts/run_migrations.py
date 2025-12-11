import asyncio
import logging
import os

from graal.api.services.migration_service import MigrationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable must be set to run migrations."
        )

    logger.info("Starting Alembic migrations before launching the API server...")
    migration_service = MigrationService(database_url)
    await migration_service.run_migrations()
    logger.info("Migrations completed successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:  # noqa: BLE001
        logger.exception("Migration script failed")
        raise
