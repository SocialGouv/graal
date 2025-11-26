"""Database initialization and seed data script for GRAAL.

This script initializes the database with seed data for local development,
including test users, sample configurations, and sample processing jobs.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graal.database.base import get_async_engine, get_async_session_maker
from graal.database.models import (
    ProcessingJob,
    SimilarityDBManifest,
    User,
    UserConfiguration,
)


async def create_seed_users(session: AsyncSession) -> dict[str, User]:
    """Create seed users for testing.

    Args:
        session: Database session

    Returns:
        Dictionary mapping user type to User object
    """
    print("Creating seed users...")

    # Admin user
    admin_user = User(
        id=uuid.uuid4(),
        proconnect_sub="admin-test-sub-001",
        email="admin@graal.com",
        email_verified=True,
        is_admin=True,
        proconnect_claims={
            "sub": "admin-test-sub-001",
            "email": "admin@graal.com",
            "email_verified": True,
        },
        last_login=datetime.now(timezone.utc),
    )
    session.add(admin_user)

    # Regular user
    regular_user = User(
        id=uuid.uuid4(),
        proconnect_sub="user-test-sub-001",
        email="user@graal.local",
        email_verified=True,
        is_admin=False,
        proconnect_claims={
            "sub": "user-test-sub-001",
            "email": "user@graal.local",
            "email_verified": True,
        },
        last_login=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    session.add(regular_user)

    await session.flush()

    print(f"  ✓ Created admin user: {admin_user.email}")
    print(f"  ✓ Created regular user: {regular_user.email}")

    return {"admin": admin_user, "user": regular_user}


async def create_seed_configurations(
    session: AsyncSession, users: dict[str, User]
) -> None:
    """Create seed configurations for testing.

    Args:
        session: Database session
        users: Dictionary of seed users
    """
    print("Creating seed configurations...")

    # Admin's configurations
    admin_config_1 = UserConfiguration(
        id=uuid.uuid4(),
        user_id=users["admin"].id,
        name="PLFSS 2024 Configuration",
        s3_config_file_path="config_graal/PLFSS_2024.xlsx",
        feature_settings={
            "summary_generation": {
                "enabled": True,
                "strategy": "dspy",
                "should_overwrite": False,
            },
            "similarity_search": {
                "enabled": True,
                "database_file": "PLFSS/2024.parquet",
            },
            "attribution": {"enabled": True},
            "allotment": {"enabled": True},
        },
        is_default=True,
    )
    session.add(admin_config_1)

    admin_config_2 = UserConfiguration(
        id=uuid.uuid4(),
        user_id=users["admin"].id,
        name="Quick Processing (No Summaries)",
        s3_config_file_path="config_graal/PLFSS_2024.xlsx",
        feature_settings={
            "summary_generation": {"enabled": False},
            "similarity_search": {
                "enabled": True,
                "database_file": "PLFSS/2024.parquet",
            },
            "attribution": {"enabled": True},
            "allotment": {"enabled": True},
        },
        is_default=False,
    )
    session.add(admin_config_2)

    # Regular user's configuration
    user_config = UserConfiguration(
        id=uuid.uuid4(),
        user_id=users["user"].id,
        name="My Default Config",
        s3_config_file_path="config_graal/PLFSS_2023.xlsx",
        feature_settings={
            "summary_generation": {"enabled": True, "strategy": "legacy"},
            "similarity_search": {
                "enabled": True,
                "database_file": "PLFSS/2023.parquet",
            },
            "attribution": {"enabled": True},
        },
        is_default=True,
    )
    session.add(user_config)

    await session.flush()

    print("  ✓ Created 3 configurations")


async def create_seed_jobs(session: AsyncSession, users: dict[str, User]) -> None:
    """Create seed processing jobs for testing.

    Args:
        session: Database session
        users: Dictionary of seed users
    """
    print("Creating seed processing jobs...")

    # Completed job
    completed_job = ProcessingJob(
        id=uuid.uuid4(),
        user_id=users["admin"].id,
        status="completed",
        percent=100,
        message="Processing completed successfully",
        input_file_s3_path="input_files/pool/test_input_001.json",
        output_file_s3_path="output_files/test_output_001.xlsx",
        config_file_used="config_graal/PLFSS_2024.xlsx",
        feature_config={
            "summary_generation": {"enabled": True, "strategy": "dspy"},
            "similarity_search": {
                "enabled": True,
                "database_file": "PLFSS/2024.parquet",
            },
        },
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=50),
        completed_at=datetime.now(timezone.utc) - timedelta(minutes=50),
        timeout_minutes=60,
    )
    session.add(completed_job)

    # Running job
    running_job = ProcessingJob(
        id=uuid.uuid4(),
        user_id=users["user"].id,
        status="running",
        percent=65,
        message="Processing amendments, similarity search in progress",
        input_file_s3_path="input_files/pool/test_input_002.json",
        output_file_s3_path=None,
        config_file_used="config_graal/PLFSS_2023.xlsx",
        feature_config={
            "summary_generation": {"enabled": False},
            "similarity_search": {
                "enabled": True,
                "database_file": "PLFSS/2023.parquet",
            },
        },
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        updated_at=datetime.now(timezone.utc),
        completed_at=None,
        timeout_minutes=60,
    )
    session.add(running_job)

    # Failed job
    failed_job = ProcessingJob(
        id=uuid.uuid4(),
        user_id=users["user"].id,
        status="failed",
        percent=25,
        message="Processing failed: Invalid input file format",
        input_file_s3_path="input_files/pool/test_input_003.json",
        output_file_s3_path=None,
        config_file_used="config_graal/PLFSS_2024.xlsx",
        feature_config={"summary_generation": {"enabled": True, "strategy": "legacy"}},
        error_details={
            "error_type": "ValidationError",
            "message": "Invalid input file format",
            "details": "Expected JSON format with 'amendments' key",
        },
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        updated_at=datetime.now(timezone.utc) - timedelta(hours=2, minutes=-5),
        completed_at=datetime.now(timezone.utc) - timedelta(hours=2, minutes=-5),
        timeout_minutes=60,
    )
    session.add(failed_job)

    # Queued job
    queued_job = ProcessingJob(
        id=uuid.uuid4(),
        user_id=users["admin"].id,
        status="queued",
        percent=0,
        message="Job queued for processing",
        input_file_s3_path="input_files/pool/test_input_004.json",
        output_file_s3_path=None,
        config_file_used="config_graal/PLFSS_2024.xlsx",
        feature_config={
            "summary_generation": {"enabled": True, "strategy": "dspy"},
            "attribution": {"enabled": True},
        },
        started_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=None,
        timeout_minutes=90,
    )
    session.add(queued_job)

    await session.flush()

    print("  ✓ Created 4 processing jobs (completed, running, failed, queued)")


async def create_seed_manifests(session: AsyncSession, users: dict[str, User]) -> None:
    """Create seed similarity database manifests for testing.

    Args:
        session: Database session
        users: Dictionary of seed users
    """
    print("Creating seed similarity database manifests...")

    # PLFSS 2024 database
    manifest_2024 = SimilarityDBManifest(
        id=uuid.uuid4(),
        created_by_user_id=users["admin"].id,
        name="PLFSS 2024",
        s3_folder_path="similarity_dbs/PLFSS/",
        s3_file_path="similarity_dbs/PLFSS/2024.parquet",
        size_bytes=15728640,  # ~15 MB
        row_count=1245,
        last_modified=datetime.now(timezone.utc) - timedelta(days=7),
        db_metadata={
            "project": "PLFSS",
            "year": 2024,
            "description": "Projet de Loi de Financement de la Sécurité Sociale 2024",
            "created_by": "Admin User",
        },
        is_active=True,
    )
    session.add(manifest_2024)

    # PLFSS 2023 database
    manifest_2023 = SimilarityDBManifest(
        id=uuid.uuid4(),
        created_by_user_id=users["admin"].id,
        name="PLFSS 2023",
        s3_folder_path="similarity_dbs/PLFSS/",
        s3_file_path="similarity_dbs/PLFSS/2023.parquet",
        size_bytes=12582912,  # ~12 MB
        row_count=978,
        last_modified=datetime.now(timezone.utc) - timedelta(days=365),
        db_metadata={
            "project": "PLFSS",
            "year": 2023,
            "description": "Projet de Loi de Financement de la Sécurité Sociale 2023",
            "created_by": "Admin User",
        },
        is_active=True,
    )
    session.add(manifest_2023)

    # Old archived database (inactive)
    manifest_old = SimilarityDBManifest(
        id=uuid.uuid4(),
        created_by_user_id=users["user"].id,
        name="Test Database (Archived)",
        s3_folder_path="similarity_dbs/archive/",
        s3_file_path="similarity_dbs/archive/test_2022.parquet",
        size_bytes=5242880,  # ~5 MB
        row_count=342,
        last_modified=datetime.now(timezone.utc) - timedelta(days=730),
        db_metadata={
            "project": "TEST",
            "year": 2022,
            "description": "Archived test database",
            "archived_reason": "End of project",
        },
        is_active=False,
    )
    session.add(manifest_old)

    await session.flush()

    print("  ✓ Created 3 similarity database manifests")


async def init_database() -> None:
    """Initialize database with seed data."""
    print("\n" + "=" * 60)
    print("GRAAL Database Initialization")
    print("=" * 60 + "\n")

    # Get database engine
    engine = get_async_engine()
    session_maker = get_async_session_maker()

    try:
        # Create all tables (if not using Alembic)
        # Note: In production, use Alembic migrations instead
        print("Checking database connection...")
        async with session_maker() as session:
            # Test connection
            await session.execute(select(1))
            print("  ✓ Database connection successful\n")

        # Create seed data
        async with session_maker() as session:
            async with session.begin():
                # Create users
                users = await create_seed_users(session)

                # Create configurations
                await create_seed_configurations(session, users)

                # Create processing jobs
                await create_seed_jobs(session, users)

                # Create similarity database manifests
                await create_seed_manifests(session, users)

                print("\n" + "=" * 60)
                print("✓ Database initialization completed successfully!")
                print("=" * 60 + "\n")

                print("Seed Data Summary:")
                print("  • Users: 2 (1 admin, 1 regular)")
                print("  • Configurations: 3")
                print("  • Processing Jobs: 4")
                print("  • Similarity DB Manifests: 3")
                print("\nTest Credentials:")
                print("  Admin: admin@graal.com (ProConnect sub: admin-test-sub-001)")
                print("  User:  user@graal.local (ProConnect sub: user-test-sub-001)")
                print("\nAccess pgAdmin at: http://localhost:5050")
                print("  Email: admin@graal.com")
                print("  Password: admin\n")

    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        raise
    finally:
        await engine.dispose()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(init_database())
    except KeyboardInterrupt:
        print("\n\nInitialization cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
