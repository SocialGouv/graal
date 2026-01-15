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

from graal.database.models import AmendmentDatabasePermission, SimilarityDBManifest
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

    async def list_all_manifests(self) -> list[SimilarityDBManifest]:
        """Return all manifests (active and inactive) ordered by creation date (newest first).

        This is intended for admin / maintenance views where historical metadata
        is useful (e.g., resolving input pool filenames from past database builds).

        Returns:
            List of SimilarityDBManifest instances
        """

        logging.debug("[SimilarityDBManifestService] Fetching all manifests")

        async with self._session_factory() as session:
            result = await session.execute(
                select(SimilarityDBManifest).order_by(
                    SimilarityDBManifest.created_at.desc()
                )
            )
            manifests = result.scalars().all()

            logging.info(
                "[SimilarityDBManifestService] Found %s manifests (active + inactive)",
                len(manifests),
            )
            return list(manifests)

    async def list_accessible_manifests(
        self, user_id: UUID
    ) -> list[SimilarityDBManifest]:
        """Return only the active manifests the user has permission to access."""

        async with self._session_factory() as session:
            result = await session.execute(
                select(SimilarityDBManifest)
                .join(
                    AmendmentDatabasePermission,
                    AmendmentDatabasePermission.db_id == SimilarityDBManifest.id,
                )
                .where(
                    AmendmentDatabasePermission.user_id == user_id,
                    SimilarityDBManifest.is_active == True,  # noqa: E712
                )
                .order_by(SimilarityDBManifest.created_at.desc())
            )
            manifests = result.scalars().all()

            logging.info(
                f"[SimilarityDBManifestService] Found {len(manifests)} accessible manifests for user {user_id}"
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

    async def resolve_s3_path_for_db(self, manifest_id: UUID) -> str:
        """
        Resolve the S3 file path for a given database ID.

        Args:
            manifest_id: UUID of the similarity database manifest

        Returns:
            S3 file path as a string

        Raises:
            ValueError: If no manifest exists for the given ID
        """
        manifest = await self.get_manifest(manifest_id)
        if manifest is None:
            raise ValueError(f"No database manifest found for id={manifest_id}")

        return manifest.s3_file_path

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

    async def delete_database_by_id(
        self,
        manifest_id: UUID,
    ) -> SimilarityDBManifest:
        """Delete a database by manifest ID, and delete the corresponding S3 file.

        This is the canonical deletion entrypoint used by admin APIs.
        It performs a hard delete of the manifest row, and removes the corresponding file from S3.

        Args:
            manifest_id: Manifest ID to delete

        Returns:
            The previously loaded manifest
        """
        logging.info(
            "[SimilarityDBManifestService] Deleting database by id=%s",
            manifest_id,
        )

        # Load the manifest once so we can derive the S3 key if needed
        manifest = await self.get_manifest(manifest_id)
        if manifest is None:
            logging.error(
                "[SimilarityDBManifestService] Manifest %s not found for deletion",
                manifest_id,
            )
            raise ValueError("Manifest not found")

        # Delete S3 file before mutating the database
        s3_path = manifest.s3_file_path
        folder = self._s3_service.similarity_db_folder
        prefix = folder if folder.endswith("/") else f"{folder}/"
        # Derive database_name as seen by DatabaseS3Service
        if s3_path.startswith(prefix):
            relative = s3_path[len(prefix) :]
        else:
            relative = s3_path
        if relative.endswith(".parquet"):
            relative = relative[:-8]
        database_name = relative

        logging.info(
            "[SimilarityDBManifestService] Deleting S3 database file for manifest %s at path %s (database_name=%s)",
            manifest_id,
            s3_path,
            database_name,
        )
        await self._s3_service.database.delete_database_file(database_name)

        async with self._session_factory() as session:
            # Attach manifest instance to this session
            db_manifest = await session.get(SimilarityDBManifest, manifest_id)
            if db_manifest is None:
                # Manifest was removed between initial read and transaction
                logging.error(
                    "[SimilarityDBManifestService] Manifest %s disappeared before deletion",
                    manifest_id,
                )
                raise ValueError("Manifest not found")

            await session.delete(db_manifest)
            await session.commit()

        # For hard deletes we return the previously loaded manifest snapshot
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
