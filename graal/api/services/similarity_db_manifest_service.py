"""
Similarity Database Manifest Service for tracking similarity databases.

This service provides CRUD operations for similarity database manifests,
allowing tracking of similarity databases stored in S3 with their metadata.

Pattern:
    - Async/await throughout for all database operations
    - Singleton pattern via get_similarity_db_manifest_service()
    - Dependency injection of S3Service for S3 operations
    - Transaction management with explicit commits and refreshes
"""

import logging
import logging.config
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.database.models import SimilarityDBManifest
from graal.database.schemas import (
    SimilarityDBManifestCreate,
    SimilarityDBManifestUpdate,
)
from graal.utils.s3.s3_service import S3Service

logging.config.fileConfig("logging.conf")


class SimilarityDBManifestService:
    """Service for managing similarity database manifests.

    This service handles all CRUD operations for similarity database manifests,
    including syncing from S3, validation, and lifecycle management.

    Attributes:
        _session_factory: Async session factory for database operations
        _s3_service: S3 service for file operations
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        s3_service: S3Service,
    ):
        """Initialize similarity database manifest service.

        Args:
            session_factory: SQLAlchemy async session factory
            s3_service: S3 service for file operations
        """
        self._session_factory = session_factory
        self._s3_service = s3_service
        logging.info("[SimilarityDBManifestService] Initialized")

    async def sync_manifests_from_s3(self, user_id: UUID) -> list[SimilarityDBManifest]:
        """Sync manifests from existing S3 files (admin-only operation).

        Populates the database with manifests for all similarity database files
        found in S3. Creates new manifests or updates existing ones if the S3
        file has been modified.

        Args:
            user_id: Admin user ID who is performing the sync

        Returns:
            List of synced SimilarityDBManifest instances

        Raises:
            Exception: If S3 operations fail
        """
        logging.info(
            f"[SimilarityDBManifestService] Syncing manifests from S3 for admin user {user_id}"
        )

        # Get all database files from S3
        database_names = await self._s3_service.database.list_database_files()
        logging.info(
            f"[SimilarityDBManifestService] Found {len(database_names)} files in S3"
        )

        synced_manifests: list[SimilarityDBManifest] = []

        async with self._session_factory() as session:
            for db_name in database_names:
                try:
                    # Get metadata from S3
                    metadata = await self._s3_service.database.get_database_metadata(
                        db_name
                    )

                    # Construct S3 paths
                    s3_folder = self._s3_service.similarity_db_folder
                    if s3_folder and not s3_folder.endswith("/"):
                        s3_folder += "/"
                    s3_file_path = f"{s3_folder}{db_name}.parquet"

                    # Check if manifest already exists
                    result = await session.execute(
                        select(SimilarityDBManifest).where(
                            SimilarityDBManifest.s3_file_path == s3_file_path
                        )
                    )
                    existing_manifest = result.scalar_one_or_none()

                    if existing_manifest:
                        # Update if S3 file has been modified
                        s3_last_modified = metadata["last_modified"]
                        if s3_last_modified > existing_manifest.last_modified:
                            logging.info(
                                f"[SimilarityDBManifestService] Updating manifest for {db_name}"
                            )
                            existing_manifest.size_bytes = metadata["size"]
                            existing_manifest.last_modified = s3_last_modified
                            existing_manifest.is_active = True
                            synced_manifests.append(existing_manifest)
                        else:
                            logging.debug(
                                f"[SimilarityDBManifestService] Manifest for {db_name} is up to date"
                            )
                            synced_manifests.append(existing_manifest)
                    else:
                        # Create new manifest
                        logging.info(
                            f"[SimilarityDBManifestService] Creating manifest for {db_name}"
                        )
                        new_manifest = SimilarityDBManifest(
                            created_by_user_id=user_id,
                            name=db_name,
                            s3_folder_path=s3_folder or "",
                            s3_file_path=s3_file_path,
                            size_bytes=metadata["size"],
                            last_modified=metadata["last_modified"],
                            is_active=True,
                        )
                        session.add(new_manifest)
                        synced_manifests.append(new_manifest)

                except Exception as e:
                    logging.error(
                        f"[SimilarityDBManifestService] Failed to sync {db_name}: {e}"
                    )
                    # Continue with other files
                    continue

            await session.commit()

            # Refresh all manifests to get current state
            for manifest in synced_manifests:
                await session.refresh(manifest)

        logging.info(
            f"[SimilarityDBManifestService] Synced {len(synced_manifests)} manifests"
        )
        return synced_manifests

    async def create_manifest(
        self, manifest_data: SimilarityDBManifestCreate, user_id: UUID
    ) -> SimilarityDBManifest:
        """Create a new manifest (typically called after building database).

        Validates that the S3 file exists before creating the manifest.

        Args:
            manifest_data: Manifest data to create
            user_id: User ID who is creating the manifest

        Returns:
            Created SimilarityDBManifest instance

        Raises:
            ValueError: If S3 file does not exist
        """
        logging.info(
            f"[SimilarityDBManifestService] Creating manifest '{manifest_data.name}'"
        )

        # Validate S3 path exists by getting metadata
        try:
            # Extract database name from s3_file_path
            file_path = manifest_data.s3_file_path
            if file_path.endswith(".parquet"):
                db_name = file_path.split("/")[-1][:-8]  # Remove .parquet
            else:
                db_name = file_path.split("/")[-1]

            await self._s3_service.database.get_database_metadata(db_name)
        except FileNotFoundError as e:
            logging.error(
                f"[SimilarityDBManifestService] S3 file not found: {manifest_data.s3_file_path}"
            )
            raise ValueError(
                f"Similarity database file not found in S3: {manifest_data.s3_file_path}"
            ) from e

        async with self._session_factory() as session:
            # Create new manifest
            new_manifest = SimilarityDBManifest(
                created_by_user_id=user_id,
                name=manifest_data.name,
                s3_folder_path=manifest_data.s3_folder_path,
                s3_file_path=manifest_data.s3_file_path,
                size_bytes=manifest_data.size_bytes,
                row_count=manifest_data.row_count,
                last_modified=manifest_data.last_modified,
                db_metadata=manifest_data.db_metadata,
                input_files=manifest_data.input_files,
                is_active=True,
            )

            session.add(new_manifest)
            await session.commit()
            await session.refresh(new_manifest)

            logging.info(
                f"[SimilarityDBManifestService] Created manifest {new_manifest.id}"
            )
            return new_manifest

    async def list_active_manifests(self) -> list[SimilarityDBManifest]:
        """Return all active manifests ordered by creation date (newest first).

        Returns:
            List of active SimilarityDBManifest instances
        """
        logging.debug("[SimilarityDBManifestService] Fetching all active manifests")

        async with self._session_factory() as session:
            result = await session.execute(
                select(SimilarityDBManifest)
                .where(SimilarityDBManifest.is_active == True)  # noqa: E712
                .order_by(SimilarityDBManifest.created_at.desc())
            )
            manifests = result.scalars().all()

            logging.info(
                f"[SimilarityDBManifestService] Found {len(manifests)} active manifests"
            )
            return list(manifests)

    async def get_manifest(self, manifest_id: UUID) -> Optional[SimilarityDBManifest]:
        """Get a specific manifest by ID.

        Args:
            manifest_id: Manifest ID

        Returns:
            SimilarityDBManifest if found, None otherwise
        """
        logging.debug(f"[SimilarityDBManifestService] Fetching manifest {manifest_id}")

        async with self._session_factory() as session:
            result = await session.execute(
                select(SimilarityDBManifest).where(
                    SimilarityDBManifest.id == manifest_id
                )
            )
            manifest = result.scalar_one_or_none()

            if manifest:
                logging.info(
                    f"[SimilarityDBManifestService] Found manifest {manifest_id}"
                )
            else:
                logging.debug(
                    f"[SimilarityDBManifestService] Manifest {manifest_id} not found"
                )

            return manifest

    async def get_manifest_by_s3_path(
        self, s3_path: str
    ) -> Optional[SimilarityDBManifest]:
        """Get manifest by S3 file path.

        Args:
            s3_path: S3 file path

        Returns:
            SimilarityDBManifest if found, None otherwise
        """
        logging.debug(
            f"[SimilarityDBManifestService] Fetching manifest by S3 path: {s3_path}"
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(SimilarityDBManifest).where(
                    SimilarityDBManifest.s3_file_path == s3_path
                )
            )
            manifest = result.scalar_one_or_none()

            if manifest:
                logging.info(
                    f"[SimilarityDBManifestService] Found manifest {manifest.id} for path {s3_path}"
                )
            else:
                logging.debug(
                    f"[SimilarityDBManifestService] No manifest found for path {s3_path}"
                )

            return manifest

    async def update_manifest(
        self, manifest_id: UUID, updates: SimilarityDBManifestUpdate
    ) -> SimilarityDBManifest:
        """Update manifest metadata.

        Args:
            manifest_id: Manifest ID to update
            updates: Fields to update

        Returns:
            Updated SimilarityDBManifest

        Raises:
            ValueError: If manifest not found
        """
        logging.info(f"[SimilarityDBManifestService] Updating manifest {manifest_id}")

        async with self._session_factory() as session:
            # Get manifest
            result = await session.execute(
                select(SimilarityDBManifest).where(
                    SimilarityDBManifest.id == manifest_id
                )
            )
            manifest = result.scalar_one_or_none()

            if not manifest:
                logging.error(
                    f"[SimilarityDBManifestService] Manifest {manifest_id} not found"
                )
                raise ValueError("Manifest not found")

            # Update fields
            if updates.name is not None:
                manifest.name = updates.name
            if updates.size_bytes is not None:
                manifest.size_bytes = updates.size_bytes
            if updates.row_count is not None:
                manifest.row_count = updates.row_count
            if updates.last_modified is not None:
                manifest.last_modified = updates.last_modified
            if updates.db_metadata is not None:
                manifest.db_metadata = updates.db_metadata
            if updates.input_files is not None:
                manifest.input_files = updates.input_files
            if updates.is_active is not None:
                manifest.is_active = updates.is_active

            await session.commit()
            await session.refresh(manifest)

            logging.info(
                f"[SimilarityDBManifestService] Updated manifest {manifest_id}"
            )
            return manifest

    async def deactivate_manifest(self, manifest_id: UUID) -> SimilarityDBManifest:
        """Soft delete: set is_active=False.

        Args:
            manifest_id: Manifest ID to deactivate

        Returns:
            Updated SimilarityDBManifest

        Raises:
            ValueError: If manifest not found
        """
        logging.info(
            f"[SimilarityDBManifestService] Deactivating manifest {manifest_id}"
        )

        async with self._session_factory() as session:
            # Get manifest
            result = await session.execute(
                select(SimilarityDBManifest).where(
                    SimilarityDBManifest.id == manifest_id
                )
            )
            manifest = result.scalar_one_or_none()

            if not manifest:
                logging.error(
                    f"[SimilarityDBManifestService] Manifest {manifest_id} not found"
                )
                raise ValueError("Manifest not found")

            # Set as inactive
            manifest.is_active = False
            await session.commit()
            await session.refresh(manifest)

            logging.info(
                f"[SimilarityDBManifestService] Deactivated manifest {manifest_id}"
            )
            return manifest


# Singleton instance
_similarity_db_manifest_service: Optional[SimilarityDBManifestService] = None


def get_similarity_db_manifest_service() -> SimilarityDBManifestService:
    """Get global similarity database manifest service instance (Singleton pattern).

    This function follows the project's service pattern for singleton instances.
    The service is initialized with database session factory and S3 service.

    Returns:
        Global similarity database manifest service instance
    """
    global _similarity_db_manifest_service
    if _similarity_db_manifest_service is None:
        logging.info("[SimilarityDBManifestService] Initializing singleton instance")

        from graal.database.base import get_async_session_maker
        from graal.utils.s3.s3_service import get_s3_service

        session_factory = get_async_session_maker()
        s3_service = get_s3_service()

        _similarity_db_manifest_service = SimilarityDBManifestService(
            session_factory, s3_service
        )

    return _similarity_db_manifest_service
