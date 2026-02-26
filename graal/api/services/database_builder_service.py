"""Service for building similarity databases via API.

This service is responsible for building a similarity DB parquet and keeping
the Postgres manifest in sync.

Important invariant:
    - ``SimilarityDBManifest.id`` is the canonical identifier.
    - ``SimilarityDBManifest.name`` is a friendly display name and **must not**
      be used as a unique identifier.
    - The S3 object key must be unique to avoid collisions when friendly names
      collide.
"""

import logging
import logging.config
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graal.api.services.job_registry import InMemoryJobRegistry
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.database.enums import DbRoleEnum
from graal.database.models import AmendmentDatabasePermission, SimilarityDBManifest
from graal.utils.config.base_config import InputFileConfig
from graal.utils.s3.s3_service import get_s3_service
from graal.utils.similarity_db_builder_service import (
    get_similarity_db_builder,
)

logging.config.fileConfig("logging.conf")


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _slugify_for_s3(value: str) -> str:
    """Convert an arbitrary string to a safe ASCII slug for S3 keys."""

    value = (value or "").strip()
    if not value:
        return "database"

    # Remove accents / diacritics
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")

    slug = ascii_value.lower().replace("_", " ")
    slug = _NON_ALNUM_RE.sub("-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug or "database"


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

    @staticmethod
    def make_unique_s3_database_name(display_name: str, manifest_id: uuid.UUID) -> str:
        """Build a human-readable but collision-proof S3 object name.

        The returned value is the *database name* expected by DatabaseS3Service
        (relative to the similarity folder, without extension).
        """

        slug = _slugify_for_s3(display_name)
        short_id = str(manifest_id).split("-")[0]
        return f"{slug}__{short_id}"

    async def start_database_build(
        self,
        job_id: str,
        config_file: str,
        display_name: str,
        s3_database_name: str,
        manifest_id: uuid.UUID,
        is_new_manifest: bool,
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
            display_name: Friendly database name (not necessarily unique)
            s3_database_name: Collision-proof S3 database key (relative, no extension)
            manifest_id: SimilarityDBManifest UUID
            is_new_manifest: True when creating a new manifest, False when appending
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
            logging.info(
                "[Job %s] Starting database build: display_name=%s, s3_database_name=%s, manifest_id=%s, is_new=%s",
                job_id,
                display_name,
                s3_database_name,
                manifest_id,
                is_new_manifest,
            )

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
            logging.info(
                "[Job %s] Uploading database to S3: %s",
                job_id,
                s3_database_name,
            )

            await self.s3_service.database.upload_database_parquet(df, s3_database_name)

            logging.info(f"[Job {job_id}] Database uploaded successfully")

            if is_new_manifest:
                await self._create_new_manifest(
                    job_id=job_id,
                    manifest_id=manifest_id,
                    display_name=display_name,
                    s3_database_name=s3_database_name,
                    files_metadata=files_metadata,
                    df=df,
                    drop_empty_columns=drop_empty_columns,
                    similarity_threshold=similarity_threshold,
                    eps=eps,
                    group_by_columns=group_by_columns,
                    config_file=config_file,
                    user_id=user_id,
                )
            else:
                await self._update_existing_manifest_by_id(
                    job_id=job_id,
                    manifest_id=manifest_id,
                    s3_database_name=s3_database_name,
                    files_metadata=files_metadata,
                    df=df,
                    drop_empty_columns=drop_empty_columns,
                    similarity_threshold=similarity_threshold,
                    eps=eps,
                    group_by_columns=group_by_columns,
                    config_file=config_file,
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

    async def _update_existing_manifest_by_id(
        self,
        job_id: str,
        manifest_id: uuid.UUID,
        s3_database_name: str,
        files_metadata: list[dict],
        df,
        drop_empty_columns: list[str],
        similarity_threshold: float,
        eps: float,
        group_by_columns: list[str],
        config_file: str,
    ) -> None:
        """Update an existing PostgreSQL similarity database manifest by ID."""
        self.job_registry.update_job(
            job_id, percent=85, message="Updating database manifest..."
        )
        logging.info(
            "[Job %s] Updating PostgreSQL database manifest id=%s (s3_database_name=%s)",
            job_id,
            manifest_id,
            s3_database_name,
        )

        # Prepare input files data
        input_files_data = self._prepare_input_files_data(files_metadata)

        # Get S3 metadata
        s3_metadata = await self._get_s3_metadata(job_id, s3_database_name)

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

        from graal.database.schemas import SimilarityDBManifestUpdate

        update_data = SimilarityDBManifestUpdate(
            size_bytes=s3_metadata.get("size", 0),
            row_count=len(df),
            last_modified=s3_metadata.get("last_modified", datetime.now(timezone.utc)),
            db_metadata=db_metadata,
            input_files={"files": input_files_data},
            is_active=True,
        )

        await self.manifest_service.update_manifest(manifest_id, update_data)

    async def _create_new_manifest(
        self,
        job_id: str,
        manifest_id: uuid.UUID,
        display_name: str,
        s3_database_name: str,
        files_metadata: list[dict],
        df,
        drop_empty_columns: list[str],
        similarity_threshold: float,
        eps: float,
        group_by_columns: list[str],
        config_file: str,
        user_id: uuid.UUID,
    ) -> None:
        """Create a new manifest and assign owner permissions.

        This is called only for *create* builds. Append builds must target an
        existing manifest by ID.
        """

        self.job_registry.update_job(
            job_id, percent=85, message="Creating database manifest..."
        )

        logging.info(
            "[Job %s] Creating new similarity DB manifest id=%s (display_name=%s, s3_database_name=%s)",
            job_id,
            manifest_id,
            display_name,
            s3_database_name,
        )

        input_files_data = self._prepare_input_files_data(files_metadata)
        s3_metadata = await self._get_s3_metadata(job_id, s3_database_name)

        s3_folder = self.s3_service.similarity_db_folder
        if s3_folder and not s3_folder.endswith("/"):
            s3_folder += "/"
        s3_file_path = f"{s3_folder}{s3_database_name}.parquet"

        projects = list({f.get("origin_project", "unknown") for f in files_metadata})
        db_metadata = {
            "projects": projects,
            "drop_empty_columns": drop_empty_columns,
            "similarity_threshold": similarity_threshold,
            "eps": eps,
            "group_by_columns": group_by_columns,
            "config_file": config_file,
        }

        # Defensive: ensure we never overwrite an existing manifest/file.
        existing = await self.manifest_service.get_manifest_by_s3_path(s3_file_path)
        if existing is not None:
            raise RuntimeError(
                "Refusing to create manifest: S3 path already exists "
                f"(s3_file_path={s3_file_path}, existing_manifest_id={existing.id})."
            )

        async with self.manifest_service._session_factory() as session:
            # IMPORTANT: we must ensure the manifest row exists before inserting
            # permissions, otherwise we can hit FK violations depending on ORM
            # flush ordering (there is no relationship configured between the
            # two mappers).
            async with session.begin():
                manifest = SimilarityDBManifest(
                    id=manifest_id,
                    created_by_user_id=user_id,
                    name=display_name,
                    s3_folder_path=s3_folder or "",
                    s3_file_path=s3_file_path,
                    size_bytes=s3_metadata.get("size", 0),
                    row_count=len(df),
                    last_modified=s3_metadata.get(
                        "last_modified", datetime.now(timezone.utc)
                    ),
                    db_metadata=db_metadata,
                    input_files={"files": input_files_data},
                    is_active=True,
                )
                session.add(manifest)
                await session.flush()

                perm = AmendmentDatabasePermission(
                    db_id=manifest_id,
                    user_id=user_id,
                    role=DbRoleEnum.owner,
                )
                session.add(perm)

            await session.refresh(manifest)

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
