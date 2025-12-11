"""API routes for similarity database builder."""

import asyncio
import json
import logging
import logging.config
from pathlib import Path
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Cookie, Form, HTTPException, Request, UploadFile

from graal.api.models.requests import (
    AppendDatabaseRequest,
    DatabaseBuildRequest,
    FileUploadReference,
)
from graal.api.models.responses import (
    DatabaseInfo,
    DatabaseListResponse,
    DatabaseManifestResponse,
    FileReferenceInfo,
    FileUploadResponse,
    JobStatus,
    ProcessingResponse,
)
from graal.api.services.authorization_service import get_authorization_service
from graal.api.services.database_builder_service import (
    DatabaseBuilderService,
    create_job_id,
)
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.utils.file_hash_service import get_file_hash_service
from graal.utils.s3.s3_service import get_s3_service

logging.config.fileConfig("logging.conf")
router = APIRouter(prefix="/databases", tags=["databases"])


def get_database_builder_service() -> DatabaseBuilderService:
    """Get the global database builder service instance."""
    from graal.api.main import database_builder_service

    return database_builder_service


# Helper functions for DRYing up common patterns


def _convert_file_ref_to_metadata(file_ref: FileReferenceInfo) -> dict[str, Any]:
    """Convert a FileReferenceInfo to metadata dictionary format.

    Args:
        file_ref: File reference to convert

    Returns:
        Dictionary with file metadata
    """
    return {
        "upload_id": file_ref.file_hash,
        "filename": file_ref.filename,
        "file_hash": file_ref.file_hash,  # Add file_hash for manifest creation
        "s3_key": file_ref.s3_key,
        "default_processing_timestamp": file_ref.metadata.get(
            "default_processing_timestamp"
        ),
        "origin_project": file_ref.metadata.get("origin_project"),
    }


def _convert_upload_ref_to_metadata(
    file_ref: FileUploadReference,
) -> dict[str, Any]:
    """Convert a FileUploadReference to metadata dictionary format.

    Args:
        file_ref: File upload reference to convert

    Returns:
        Dictionary with file metadata
    """
    return {
        "upload_id": file_ref.upload_id,
        "filename": file_ref.filename,
        "file_hash": file_ref.file_hash,
        "s3_key": file_ref.s3_key,
        "default_processing_timestamp": file_ref.metadata.default_processing_timestamp,
        "origin_project": file_ref.metadata.origin_project,
    }


def _create_task_completion_callback(job_id: str, task_type: str):
    """Create a callback function for logging task completion.

    Args:
        job_id: The job ID for logging
        task_type: Description of task type (e.g., 'Background task', 'Append task')

    Returns:
        Callback function for asyncio task
    """

    def _log_task_result(task_future):
        try:
            task_future.result()
            logging.info(f"[API] {task_type} completed successfully for job {job_id}")
        except Exception as e:
            logging.error(
                f"[API] {task_type} failed for job {job_id}: {e}", exc_info=True
            )

    return _log_task_result


def _ensure_temp_upload_dir() -> Path:
    """Ensure the temp upload directory exists.

    Returns:
        Path to the temp upload directory
    """
    temp_dir = Path("tmp/db_builder_uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


async def _download_file_to_temp(
    s3_service, file_metadata: dict[str, Any], temp_dir: Path
) -> None:
    """Download a file from S3 pool to temp directory if not already present.

    Args:
        s3_service: S3 service instance
        file_metadata: Dictionary with s3_key, upload_id, and filename
        temp_dir: Temporary directory path
    """
    s3_key = file_metadata["s3_key"]
    upload_id = file_metadata["upload_id"]
    filename = file_metadata["filename"]

    temp_file_path = temp_dir / f"{upload_id}_{filename}"

    # Check if file already exists before downloading
    if temp_file_path.exists():
        logging.debug(f"[API] File already exists in temp: {temp_file_path.name}")
        return

    # Download file from S3
    file_content = await s3_service.download_from_input_pool(s3_key)
    with open(temp_file_path, "wb") as f:
        f.write(file_content)
    logging.info(f"[API] Downloaded file from pool to temp: {temp_file_path.name}")


@router.get("", response_model=DatabaseListResponse)
async def list_databases():
    """List all available similarity databases from PostgreSQL manifests.

    Returns:
        DatabaseListResponse: List of available databases with metadata

    Raises:
        HTTPException: 500 if listing fails
    """
    logging.info("[API] Listing available similarity databases from manifests")

    try:
        manifest_service = get_similarity_db_manifest_service()
        manifests = await manifest_service.list_active_manifests()

        # Convert manifests to DatabaseInfo format
        databases = [
            DatabaseInfo(
                name=manifest.name,
                size_bytes=manifest.size_bytes,
                last_modified=manifest.last_modified,
            )
            for manifest in manifests
        ]

        logging.info(
            f"[API] Found {len(databases)} similarity databases from manifests"
        )
        return DatabaseListResponse(databases=databases, total=len(databases))

    except Exception as e:
        logging.error(f"[API] Error listing databases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list databases") from e


@router.post("/upload-file", response_model=FileUploadResponse)
async def upload_amendment_file(
    file: UploadFile,
    metadata: Annotated[str, Form()],
) -> FileUploadResponse:
    """Upload an amendment file for database building.

    The file is checked against the pool using hash-based deduplication.
    If the file already exists, returns reference to existing file.
    Otherwise uploads to pool and returns new file reference.

    Args:
        file: The amendment file to upload
        metadata: JSON string with required default_processing_timestamp and origin_project

    Returns:
        FileUploadResponse: Upload information including hash, s3_key, and deduplication status

    Raises:
        HTTPException: 500 if upload fails
    """
    try:
        # Parse metadata
        file_metadata = json.loads(metadata)

        # Read file content
        contents = await file.read()
        filename = file.filename or "unknown"

        logging.info(
            f"[API] Processing file upload: {filename} ({len(contents)} bytes)"
        )

        # Get services
        hash_service = get_file_hash_service()
        s3_service = get_s3_service()

        # Compute file hash
        file_hash = await hash_service.compute_file_hash(contents)
        logging.info(f"[API] Computed hash for {filename}: {file_hash}")

        # Check if file exists in pool by listing files with this hash prefix
        existing_files = await s3_service.pool.list_pool_files_by_hash_prefix(file_hash)
        already_existed = len(existing_files) > 0

        # Generate S3 key for the file
        s3_key = hash_service.hash_to_s3_key(file_hash, filename)

        if already_existed:
            logging.info(f"[API] File already exists in pool: {s3_key}")
        else:
            # Upload new file to pool
            await s3_service.pool.upload_to_input_pool(contents, s3_key)
            logging.info(f"[API] Uploaded new file to pool: {s3_key}")

        # Generate upload_id for backward compatibility (use hash as ID)
        upload_id = file_hash

        # Also save to temp directory for backward compatibility with existing build logic
        temp_dir = _ensure_temp_upload_dir()
        file_path = temp_dir / f"{upload_id}_{filename}"
        with open(file_path, "wb") as f:
            f.write(contents)

        logging.info(
            f"[API] File processed successfully: {filename} "
            f"(hash: {file_hash}, existed: {already_existed})"
        )

        return FileUploadResponse(
            upload_id=upload_id,
            filename=filename,
            file_hash=file_hash,
            s3_key=s3_key,
            already_existed=already_existed,
            size=len(contents),
            metadata=file_metadata,
        )

    except json.JSONDecodeError as e:
        logging.error(f"[API] Invalid metadata JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid metadata JSON") from e
    except Exception as e:
        logging.error(f"[API] Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file") from e


@router.post("/build", response_model=ProcessingResponse)
async def build_database(
    request: DatabaseBuildRequest,
    http_request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """Start building a similarity database in the background.

    Args:
        request: DatabaseBuildRequest with build configuration
        http_request: FastAPI request object
        session: Session cookie value

    Returns:
        ProcessingResponse: Job information for tracking build progress

    Raises:
        HTTPException: 401 if not authenticated, 400 for validation errors, 500 for build errors

    Example request:
        {
            "config_file": "Fichier de configuration GRAAL - DSS - latest.xlsx",
            "database_name": "PLFSS_2024",
            "files_metadata": [
                {
                    "filename": "amendments_2024.json",
                    "default_processing_timestamp": 1704067200,
                    "origin_project": "PLFSS 2024"
                }
            ],
            "drop_empty_columns": ["Réponse"],
            "similarity_threshold": 0.99,
            "eps": 0.4,
            "group_by_columns": ["Lecture", "origin_project", "Num article"]
        }
    """
    logging.info(f"[API] Received database build request: {request.database_name}")

    try:
        # Get current user for manifest creation
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(http_request, session)
        user_id = UUID(current_user.user_id)

        # Create job
        job_id = create_job_id()
        builder_service = get_database_builder_service()

        # Create job entry in registry
        builder_service.job_registry.create_job(
            job_id=job_id, input_file_path=f"database_build_{request.database_name}"
        )

        logging.info(
            f"[API] Created job {job_id} for database build: {request.database_name}"
        )

        # Start background task
        logging.info(f"[API] About to create background task for job {job_id}")
        logging.info(f"[API] Config file: {request.config_file}")
        logging.info(f"[API] Database name: {request.database_name}")
        logging.info(f"[API] File references: {request.file_references}")
        logging.info(f"[API] Number of file references: {len(request.file_references)}")

        try:
            files_metadata = [
                _convert_upload_ref_to_metadata(ref) for ref in request.file_references
            ]
            logging.info(f"[API] Converted file references to dicts: {files_metadata}")
        except Exception as e:
            logging.error(
                f"[API] Error converting file references to dict: {e}", exc_info=True
            )
            raise

        try:
            task = asyncio.create_task(
                builder_service.start_database_build(
                    job_id=job_id,
                    config_file=request.config_file,
                    database_name=request.database_name,
                    files_metadata=files_metadata,
                    drop_empty_columns=request.drop_empty_columns,
                    similarity_threshold=request.similarity_threshold,
                    eps=request.eps,
                    group_by_columns=request.group_by_columns,
                    user_id=user_id,
                )
            )
            logging.info(f"[API] Background task created successfully: {task}")
        except Exception as e:
            logging.error(f"[API] Error creating background task: {e}", exc_info=True)
            raise

        # Add callback to log task completion or errors
        task.add_done_callback(
            _create_task_completion_callback(job_id, "Background task")
        )

        logging.info(
            f"[API] Database build job started successfully - job_id: {job_id}, database: {request.database_name}"
        )
        return ProcessingResponse(
            job_id=job_id, status=JobStatus.queued, message="Database build job started"
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(
            f"[API] Error starting database build for {request.database_name}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to start database build: {str(e)}"
        ) from e


@router.delete("/uploads/{upload_id}")
async def delete_uploaded_file(upload_id: str):
    """Delete an uploaded file that's no longer needed.

    This endpoint is idempotent - if the file doesn't exist, it returns success
    since the desired state (file not existing) is already achieved.

    Args:
        upload_id: The upload ID of the file to delete

    Returns:
        dict: Success message

    Raises:
        HTTPException: 500 if deletion fails
    """
    try:
        temp_upload_dir = _ensure_temp_upload_dir()

        # Find file with this upload_id
        files_deleted = 0
        for file_path in temp_upload_dir.glob(f"{upload_id}_*"):
            file_path.unlink()
            logging.info(f"[API] Deleted uploaded file: {file_path}")
            files_deleted += 1

        if files_deleted > 0:
            return {"message": "File deleted successfully"}
        else:
            # File doesn't exist - return success (idempotent deletion)
            logging.info(f"[API] File already deleted or not found: {upload_id}")
            return {"message": "File already deleted or not found"}

    except Exception as e:
        logging.error(f"[API] Error deleting uploaded file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete file") from e


def _find_manifest_by_name(all_manifests: list, database_name: str):
    """Find manifest by database name.

    Args:
        all_manifests: List of all active manifests
        database_name: Name of the database to find

    Returns:
        The matching manifest or None

    Raises:
        HTTPException: If manifest not found
    """
    for manifest in all_manifests:
        if manifest.name == database_name:
            return manifest

    raise HTTPException(
        status_code=404,
        detail=f"Database '{database_name}' not found. Create it first using the build endpoint.",
    )


def _extract_existing_files_metadata(manifest) -> list[dict]:
    """Extract existing files metadata from manifest.

    Args:
        manifest: Database manifest containing input_files

    Returns:
        List of existing files metadata dictionaries
    """
    existing_files_metadata = []
    if manifest.input_files and "files" in manifest.input_files:
        for file_data in manifest.input_files["files"]:
            existing_files_metadata.append(
                {
                    "upload_id": file_data["file_hash"],
                    "filename": file_data["filename"],
                    "file_hash": file_data["file_hash"],
                    "s3_key": file_data["s3_key"],
                    "uploaded_at": file_data["uploaded_at"],
                    "default_processing_timestamp": file_data.get("metadata", {}).get(
                        "default_processing_timestamp"
                    ),
                    "origin_project": file_data.get("metadata", {}).get(
                        "origin_project"
                    ),
                }
            )
    return existing_files_metadata


def _check_for_duplicates(existing_files: list[dict], new_files: list[dict]) -> None:
    """Check for duplicate files and raise error if found.

    Args:
        existing_files: List of existing file metadata
        new_files: List of new file metadata

    Raises:
        HTTPException: If duplicate files found
    """
    existing_hashes = {f["upload_id"] for f in existing_files}
    new_hashes = {f["upload_id"] for f in new_files}
    duplicate_hashes = existing_hashes & new_hashes

    if duplicate_hashes:
        duplicate_files = [
            f["filename"] for f in new_files if f["upload_id"] in duplicate_hashes
        ]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot append: files already exist in database: {', '.join(duplicate_files)}",
        )


async def _download_all_files(
    s3_service, files_metadata: list[dict], temp_dir: Path
) -> None:
    """Download all files from S3 to temp directory.

    Args:
        s3_service: S3 service instance
        files_metadata: List of file metadata to download
        temp_dir: Temporary directory path
    """
    for file_metadata in files_metadata:
        await _download_file_to_temp(s3_service, file_metadata, temp_dir)


@router.post("/{database_name}/append", response_model=ProcessingResponse)
async def append_to_database(
    database_name: str,
    request: AppendDatabaseRequest,
    http_request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """Append new files to an existing database by rebuilding with all files.

    This endpoint loads the existing database manifest, combines the existing files
    with the new file references, and triggers a full rebuild of the database.

    Args:
        database_name: Name of the database to append to
        request: AppendDatabaseRequest with new files and build configuration
        http_request: FastAPI request object
        session: Session cookie value

    Returns:
        ProcessingResponse: Job information for tracking append progress
    """
    logging.info(f"[API] Received append request for database: {database_name}")

    # Validate request
    if not request.file_references:
        raise HTTPException(
            status_code=400,
            detail="Cannot append: no files provided. Include at least one file in file_references.",
        )

    try:
        # Get current user for manifest creation
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(http_request, session)
        user_id = UUID(current_user.user_id)

        # Get PostgreSQL manifest service and find manifest
        pg_manifest_service = get_similarity_db_manifest_service()
        all_manifests = await pg_manifest_service.list_active_manifests()
        manifest = _find_manifest_by_name(all_manifests, database_name)

        logging.info(f"[API] Loaded PostgreSQL manifest for {database_name}")

        # Convert new file references to metadata format
        new_files_metadata = [
            _convert_upload_ref_to_metadata(file_ref)
            for file_ref in request.file_references
        ]

        # Extract existing files metadata from manifest
        existing_files_metadata = _extract_existing_files_metadata(manifest)
        logging.info(
            f"[API] Found {len(existing_files_metadata)} existing files in manifest"
        )

        # Check for duplicate files before combining
        _check_for_duplicates(existing_files_metadata, new_files_metadata)

        # Combine all files
        all_files_metadata = existing_files_metadata + new_files_metadata
        logging.info(
            f"[API] Appending {len(new_files_metadata)} new files to {len(existing_files_metadata)} existing files"
        )

        # Download files from S3 pool to temp directory for building
        temp_dir = _ensure_temp_upload_dir()
        s3_service = get_s3_service()
        await _download_all_files(s3_service.pool, all_files_metadata, temp_dir)

        # Create job for rebuild
        job_id = create_job_id()
        builder_service = get_database_builder_service()
        builder_service.job_registry.create_job(
            job_id=job_id, input_file_path=f"database_append_{database_name}"
        )

        logging.info(
            f"[API] Created job {job_id} for appending to database: {database_name}"
        )

        # Start background task for rebuild with provided config file
        task = asyncio.create_task(
            builder_service.start_database_build(
                job_id=job_id,
                config_file=request.config_file,
                database_name=database_name,
                files_metadata=all_files_metadata,
                drop_empty_columns=request.drop_empty_columns,
                similarity_threshold=request.similarity_threshold,
                eps=request.eps,
                group_by_columns=request.group_by_columns,
                user_id=user_id,
            )
        )

        # Add callback to log task completion or errors
        task.add_done_callback(_create_task_completion_callback(job_id, "Append task"))

        logging.info(
            f"[API] Database append job started successfully - job_id: {job_id}, database: {database_name}"
        )
        return ProcessingResponse(
            job_id=job_id,
            status=JobStatus.queued,
            message="Database append job started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(
            f"[API] Error appending to database {database_name}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to append to database: {str(e)}"
        ) from e


@router.get("/{database_name}/manifest", response_model=DatabaseManifestResponse)
async def get_database_manifest(database_name: str):
    """Retrieve the manifest for a database showing all input files.

    Args:
        database_name: Name of the database

    Returns:
        DatabaseManifestResponse: Manifest with list of files and metadata

    Raises:
        HTTPException: 404 if database/manifest not found, 500 for other errors
    """
    logging.info(f"[API] Retrieving manifest for database: {database_name}")

    try:
        # Get PostgreSQL manifest service
        pg_manifest_service = get_similarity_db_manifest_service()

        # Get all active manifests and find the one matching database_name
        logging.info(f"[API] Loading PostgreSQL manifest for: {database_name}")
        all_manifests = await pg_manifest_service.list_active_manifests()

        manifest = None
        for m in all_manifests:
            if m.name == database_name:
                manifest = m
                break

        if not manifest:
            raise FileNotFoundError(f"No manifest found for database: {database_name}")

        logging.info(
            f"[API] Successfully loaded PostgreSQL manifest for: {database_name}"
        )

        # Extract input files from the manifest's input_files JSONB field
        files = []
        if manifest.input_files and "files" in manifest.input_files:
            # New format: Full file details in input_files
            logging.info(
                f"[API] Loading {len(manifest.input_files['files'])} files from input_files field"
            )
            for file_data in manifest.input_files["files"]:
                files.append(
                    FileReferenceInfo(
                        upload_id=file_data["file_hash"],
                        filename=file_data["filename"],
                        file_hash=file_data["file_hash"],
                        s3_key=file_data["s3_key"],
                        uploaded_at=file_data["uploaded_at"],
                        metadata=file_data.get("metadata", {}),
                    )
                )
        else:
            logging.warning(
                "[API] No input files found in manifest. "
                "This database was created with old code and must be rebuilt to see files."
            )

        logging.info(
            f"[API] Retrieved manifest for {database_name} with {len(files)} files"
        )

        return DatabaseManifestResponse(
            database_name=manifest.name,
            created_at=manifest.created_at.isoformat(),
            last_updated_at=manifest.last_modified.isoformat(),
            files=files,
            total_files=len(files),
        )

    except FileNotFoundError as e:
        logging.warning(f"[API] Manifest not found for database: {database_name}")
        raise HTTPException(
            status_code=404,
            detail=f"Manifest not found for database '{database_name}'.",
        ) from e
    except Exception as e:
        logging.error(
            f"[API] Error retrieving manifest for {database_name}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve manifest: {str(e)}"
        ) from e
