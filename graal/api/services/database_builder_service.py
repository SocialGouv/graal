"""Service for building similarity databases via API."""

import logging
import logging.config
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graal.api.services.job_registry import InMemoryJobRegistry
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.database.models import AmendmentDatabasePermission, SimilarityDBManifest
from graal.utils.config.base_config import InputFileConfig
from graal.utils.s3.s3_service import get_s3_service
from graal.utils.similarity_db_builder_service import (
    get_similarity_db_builder,
)

logging.config.fileConfig("logging.conf")


class DatabaseBuilderService:
    """Service for building similarity databases in the background."""

    def __init__(self, job_registry: InMemoryJobRegistry):
        """Initialize the database builder service.

        Args:
            job_registry: Job registry for tracking build progress
        """
        self.job_registry = job_registry
        self.db_builder = get_similarity_db_builder()
        self.s3_service = get_s3_service()
        self.manifest_service = get_similarity_db_manifest_service()

    async def start_database_build(
        self,
        job_id: str,
        config_file: str,
        database_name: str,
        files_metadata: list[dict],
        drop_empty_columns: list[str],
        similarity_threshold: float,
        eps: float,
        group_by_columns: list[str],
        user_id: uuid.UUID,
    ) -> None:
        """Build database in background and upload to S3.

        Args:
            job_id: Unique job identifier
            config_file: Office configuration Excel file to use
            database_name: Name for the database (without extension)
            files_metadata: List of file metadata dictionaries
            drop_empty_columns: Columns where empty rows should be dropped
            similarity_threshold: Threshold for Levenshtein refinement
            eps: Epsilon value for DBSCAN clustering
            group_by_columns: Columns to group by during clustering
            user_id: User ID who initiated the build
        """
        try:
            # Update job status to running
            self.job_registry.update_job(job_id, status="running", percent=0)
            logging.info(f"[Job {job_id}] Starting database build: {database_name}")

            # Load amendment files from temporary upload directory
            amendment_files = await self._load_amendment_files(job_id, files_metadata)

            # Build database
            self.job_registry.update_job(
                job_id, percent=40, message="Building similarity database..."
            )
            logging.info(
                f"[Job {job_id}] Starting database build with {len(amendment_files)} files"
            )
            logging.info(f"[Job {job_id}] Config file from UI: {config_file}")
            logging.info(
                f"[Job {job_id}] Config file in builder: {self.db_builder._office_config_file_path}"
            )

            df = await self.db_builder.build_database(
                amendment_files=amendment_files,
                drop_empty_columns=drop_empty_columns,
                similarity_threshold=similarity_threshold,
                eps=eps,
                group_by_columns=group_by_columns,
                office_config_file_path=config_file,
            )

            logging.info(
                f"[Job {job_id}] Database built successfully with {len(df)} rows"
            )

            # Upload to S3
            self.job_registry.update_job(
                job_id, percent=80, message="Uploading database to S3..."
            )
            logging.info(f"[Job {job_id}] Uploading database to S3: {database_name}")

            await self.s3_service.database.upload_database_parquet(df, database_name)

            logging.info(f"[Job {job_id}] Database uploaded successfully")

            # Create or update PostgreSQL similarity database manifest
            await self._create_or_update_manifest(
                job_id=job_id,
                database_name=database_name,
                files_metadata=files_metadata,
                df=df,
                drop_empty_columns=drop_empty_columns,
                similarity_threshold=similarity_threshold,
                eps=eps,
                group_by_columns=group_by_columns,
                config_file=config_file,
                user_id=user_id,
            )

            # Cleanup uploaded files from temp directory
            await self._cleanup_temp_files(job_id, amendment_files)

            # Complete
            self.job_registry.update_job(
                job_id,
                percent=100,
                message="Database build complete!",
                status="completed",
            )
            logging.info(f"[Job {job_id}] Database build completed successfully")

        except Exception as e:
            logging.error(f"[Job {job_id}] Error building database: {e}", exc_info=True)
            self.job_registry.update_job(
                job_id, status="failed", error=str(e), message=f"Build failed: {str(e)}"
            )
            raise

    async def _load_amendment_files(
        self, job_id: str, files_metadata: list[dict]
    ) -> dict[Path, InputFileConfig]:
        """Load amendment files from temporary upload directory.

        Args:
            job_id: Unique job identifier
            files_metadata: List of file metadata dictionaries

        Returns:
            Dictionary mapping file paths to their configurations

        Raises:
            FileNotFoundError: If an uploaded file is not found
        """
        temp_upload_dir = Path("tmp/db_builder_uploads")
        self.job_registry.update_job(
            job_id,
            percent=10,
            message="Loading uploaded amendment files...",
        )
        amendment_files: dict[Path, InputFileConfig] = {}

        for idx, file_ref in enumerate(files_metadata):
            upload_id = file_ref["upload_id"]
            filename = file_ref["filename"]
            progress = 10 + int((idx / len(files_metadata)) * 30)  # 10-40%
            self.job_registry.update_job(
                job_id, percent=progress, message=f"Loading {filename}..."
            )
            logging.info(
                f"[Job {job_id}] Processing file {idx + 1}/{len(files_metadata)}: {filename}"
            )

            # Find uploaded file
            file_path = temp_upload_dir / f"{upload_id}_{filename}"

            if not file_path.exists():
                raise FileNotFoundError(f"Uploaded file not found: {filename}")

            config: InputFileConfig = {
                "default_processing_timestamp": file_ref[
                    "default_processing_timestamp"
                ],
                "origin_project": file_ref["origin_project"],
            }
            amendment_files[file_path] = config

        return amendment_files

    async def _create_or_update_manifest(
        self,
        job_id: str,
        database_name: str,
        files_metadata: list[dict],
        df,
        drop_empty_columns: list[str],
        similarity_threshold: float,
        eps: float,
        group_by_columns: list[str],
        config_file: str,
        user_id: uuid.UUID,
    ) -> None:
        """Create or update PostgreSQL similarity database manifest.

        Args:
            job_id: Unique job identifier
            database_name: Name for the database
            files_metadata: List of file metadata dictionaries
            df: Built DataFrame
            drop_empty_columns: Columns where empty rows should be dropped
            similarity_threshold: Threshold for Levenshtein refinement
            eps: Epsilon value for DBSCAN clustering
            group_by_columns: Columns to group by during clustering
            config_file: Office configuration Excel file used
            user_id: User ID who initiated the build
        """
        self.job_registry.update_job(
            job_id, percent=85, message="Updating database manifest..."
        )
        logging.info(
            f"[Job {job_id}] Creating/updating PostgreSQL database manifest for: {database_name}"
        )

        # Prepare input files data
        input_files_data = self._prepare_input_files_data(files_metadata)

        # Get S3 metadata
        s3_metadata = await self._get_s3_metadata(job_id, database_name)

        # Construct S3 paths
        s3_folder = self.s3_service.similarity_db_folder
        if s3_folder and not s3_folder.endswith("/"):
            s3_folder += "/"
        s3_file_path = f"{s3_folder}{database_name}.parquet"

        # Extract project names for metadata
        projects = list({f.get("origin_project", "unknown") for f in files_metadata})

        # Build metadata dictionary
        db_metadata = {
            "projects": projects,
            "drop_empty_columns": drop_empty_columns,
            "similarity_threshold": similarity_threshold,
            "eps": eps,
            "group_by_columns": group_by_columns,
            "config_file": config_file,
        }

        # Check if manifest already exists (for append operations)
        existing_manifest = await self.manifest_service.get_manifest_by_s3_path(
            s3_file_path
        )

        if existing_manifest:
            await self._update_existing_manifest(
                job_id,
                existing_manifest,
                s3_metadata,
                len(df),
                db_metadata,
                input_files_data,
            )
        else:
            await self._create_new_manifest(
                job_id,
                database_name,
                s3_folder,
                s3_file_path,
                s3_metadata,
                len(df),
                db_metadata,
                input_files_data,
                user_id,
            )

    def _prepare_input_files_data(self, files_metadata: list[dict]) -> list[dict]:
        """Prepare input files data for PostgreSQL storage.

        Args:
            files_metadata: List of file metadata dictionaries

        Returns:
            List of formatted file data dictionaries
        """
        input_files_data = []
        for file_meta in files_metadata:
            # Preserve uploaded_at if it exists (for append operations)
            # Otherwise use current timestamp (for newly uploaded files)
            uploaded_at_str = (
                file_meta["uploaded_at"]
                if "uploaded_at" in file_meta and file_meta["uploaded_at"]
                else datetime.now(timezone.utc).isoformat()
            )

            file_data = {
                "file_hash": file_meta["file_hash"],
                "filename": file_meta["filename"],
                "s3_key": file_meta["s3_key"],
                "uploaded_at": uploaded_at_str,
                "metadata": {
                    "default_processing_timestamp": file_meta[
                        "default_processing_timestamp"
                    ],
                    "origin_project": file_meta["origin_project"],
                },
            }
            input_files_data.append(file_data)

        return input_files_data

    async def _get_s3_metadata(self, job_id: str, database_name: str) -> dict[str, Any]:
        """Get metadata from S3 for the database.

        Args:
            job_id: Unique job identifier
            database_name: Name of the database

        Returns:
            Dictionary containing S3 metadata (size, last_modified)
        """
        try:
            return await self.s3_service.database.get_database_metadata(database_name)
        except Exception as e:
            logging.warning(
                f"[Job {job_id}] Could not get S3 metadata, using defaults: {e}"
            )
            return {
                "size": 0,
                "last_modified": datetime.now(timezone.utc),
            }

    async def _update_existing_manifest(
        self,
        job_id: str,
        existing_manifest,
        s3_metadata: dict,
        row_count: int,
        db_metadata: dict,
        input_files_data: list[dict],
    ) -> None:
        """Update an existing manifest.

        Args:
            job_id: Unique job identifier
            existing_manifest: Existing manifest object
            s3_metadata: S3 metadata dictionary
            row_count: Number of rows in the database
            db_metadata: Database metadata dictionary
            input_files_data: List of input file data dictionaries
        """
        logging.info(
            f"[Job {job_id}] Updating existing manifest {existing_manifest.id}"
        )
        from graal.database.schemas import SimilarityDBManifestUpdate

        update_data = SimilarityDBManifestUpdate(
            size_bytes=s3_metadata.get("size", 0),
            row_count=row_count,
            last_modified=s3_metadata.get("last_modified", datetime.now(timezone.utc)),
            db_metadata=db_metadata,
            input_files={"files": input_files_data},
            is_active=True,
        )
        await self.manifest_service.update_manifest(existing_manifest.id, update_data)
        logging.info(
            f"[Job {job_id}] Similarity database manifest updated successfully"
        )

    async def _create_new_manifest(
        self,
        job_id: str,
        database_name: str,
        s3_folder: str,
        s3_file_path: str,
        s3_metadata: dict,
        row_count: int,
        db_metadata: dict,
        input_files_data: list[dict],
        user_id: uuid.UUID,
    ) -> None:
        """Create a new manifest.

        Args:
            job_id: Unique job identifier
            database_name: Name for the database
            s3_folder: S3 folder path
            s3_file_path: S3 file path
            s3_metadata: S3 metadata dictionary
            row_count: Number of rows in the database
            db_metadata: Database metadata dictionary
            input_files_data: List of input file data dictionaries
            user_id: User ID who initiated the build
        """
        logging.info(f"[Job {job_id}] Creating new manifest")

        # Transaction-safe creation of manifest + owner permission
        async with self.manifest_service._session_factory() as session:
            manifest = SimilarityDBManifest(
                created_by_user_id=user_id,
                name=database_name,
                s3_folder_path=s3_folder or "",
                s3_file_path=s3_file_path,
                size_bytes=s3_metadata.get("size", 0),
                row_count=row_count,
                last_modified=s3_metadata.get(
                    "last_modified", datetime.now(timezone.utc)
                ),
                db_metadata=db_metadata,
                input_files={"files": input_files_data},
                is_active=True,
            )
            session.add(manifest)
            await session.flush()  # ensure manifest.id is available

            # Assign creator as owner
            perm = AmendmentDatabasePermission(
                db_id=manifest.id,
                user_id=user_id,
                role="owner",
            )
            session.add(perm)

            await session.commit()
            await session.refresh(manifest)

        logging.info(
            f"[Job {job_id}] Similarity database manifest created successfully"
        )

    async def _cleanup_temp_files(
        self, job_id: str, amendment_files: dict[Path, InputFileConfig]
    ) -> None:
        """Cleanup temporary uploaded files.

        Args:
            job_id: Unique job identifier
            amendment_files: Dictionary of file paths to clean up
        """
        self.job_registry.update_job(
            job_id, percent=95, message="Cleaning up temporary files..."
        )
        for file_path in amendment_files.keys():
            try:
                file_path.unlink()
                logging.info(f"[Job {job_id}] Deleted temporary file: {file_path}")
            except Exception as e:
                logging.warning(
                    f"[Job {job_id}] Failed to cleanup temporary file {file_path}: {e}"
                )


def create_job_id() -> str:
    """Create a unique job ID.

    Returns:
        str: Unique job identifier
    """
    return str(uuid.uuid4())
