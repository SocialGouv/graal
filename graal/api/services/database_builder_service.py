"""Service for building similarity databases via API."""

import logging
import logging.config
import uuid
from datetime import datetime, timezone
from pathlib import Path

from graal.api.services.job_registry import InMemoryJobRegistry
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.database.schemas import SimilarityDBManifestCreate
from graal.utils.config.base_config import InputFileConfig
from graal.utils.s3_service import get_s3_service
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

            await self.s3_service.upload_database_parquet(df, database_name)

            logging.info(f"[Job {job_id}] Database uploaded successfully")

            # Create PostgreSQL similarity database manifest with input files
            self.job_registry.update_job(
                job_id, percent=85, message="Creating database manifest..."
            )
            logging.info(
                f"[Job {job_id}] Creating PostgreSQL database manifest for: {database_name}"
            )

            # Convert files_metadata to input_files format for PostgreSQL
            input_files_data = []
            for file_meta in files_metadata:
                # Preserve uploaded_at if it exists (for append operations with existing files)
                # Otherwise use current timestamp (for newly uploaded files)
                if "uploaded_at" in file_meta and file_meta["uploaded_at"]:
                    uploaded_at_str = file_meta["uploaded_at"]
                else:
                    uploaded_at_str = datetime.now(timezone.utc).isoformat()

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

            # Get metadata from S3 to populate manifest
            try:
                s3_metadata = await self.s3_service.get_database_metadata(database_name)
            except Exception as e:
                logging.warning(
                    f"[Job {job_id}] Could not get S3 metadata, using defaults: {e}"
                )
                s3_metadata = {
                    "size": 0,
                    "last_modified": datetime.now(timezone.utc),
                }

            # Construct S3 paths
            s3_folder = self.s3_service._similarity_db_folder
            if s3_folder and not s3_folder.endswith("/"):
                s3_folder += "/"
            s3_file_path = f"{s3_folder}{database_name}.parquet"

            # Extract project names for metadata
            projects = list(
                {f.get("origin_project", "unknown") for f in files_metadata}
            )

            # Create manifest data
            manifest_data = SimilarityDBManifestCreate(
                name=database_name,
                s3_folder_path=s3_folder or "",
                s3_file_path=s3_file_path,
                size_bytes=s3_metadata.get("size", 0),
                row_count=len(df),
                last_modified=s3_metadata.get(
                    "last_modified", datetime.now(timezone.utc)
                ),
                db_metadata={
                    "projects": projects,
                    "drop_empty_columns": drop_empty_columns,
                    "similarity_threshold": similarity_threshold,
                    "eps": eps,
                    "group_by_columns": group_by_columns,
                    "config_file": config_file,
                },
                input_files={
                    "files": input_files_data
                },  # Store input files in PostgreSQL
            )

            # Create manifest in database
            await self.manifest_service.create_manifest(manifest_data, user_id)

            logging.info(
                f"[Job {job_id}] Similarity database manifest created successfully"
            )

            # Cleanup uploaded files from temp directory
            # Note: Files remain in S3 pool for reuse
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


def create_job_id() -> str:
    """Create a unique job ID.

    Returns:
        str: Unique job identifier
    """
    return str(uuid.uuid4())
