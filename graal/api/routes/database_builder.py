"""API routes for similarity database builder."""

import asyncio
import json
import logging
import logging.config
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile

from graal.api.models.requests import DatabaseBuildRequest
from graal.api.models.responses import (
    DatabaseInfo,
    DatabaseListResponse,
    JobStatus,
    ProcessingResponse,
)
from graal.api.services.database_builder_service import (
    DatabaseBuilderService,
    create_job_id,
)
from graal.utils.s3_service import get_s3_service

logging.config.fileConfig("logging.conf")
router = APIRouter(prefix="/databases", tags=["databases"])


def get_database_builder_service() -> DatabaseBuilderService:
    """Get the global database builder service instance."""
    from graal.api.main import database_builder_service

    return database_builder_service


@router.get("", response_model=DatabaseListResponse)
async def list_databases():
    """List all available similarity databases from S3.

    Returns:
        DatabaseListResponse: List of available databases with metadata

    Raises:
        HTTPException: 500 if listing fails
    """
    logging.info("[API] Listing available similarity databases")

    try:
        s3_service = get_s3_service()
        database_names = await s3_service.list_database_files()

        # Get metadata for each database
        databases = []
        for name in database_names:
            try:
                metadata = await s3_service.get_database_metadata(name)
                databases.append(
                    DatabaseInfo(
                        name=name,
                        size_bytes=metadata["size"],
                        last_modified=metadata["last_modified"],
                    )
                )
            except Exception as e:
                logging.warning(f"Failed to get metadata for database {name}: {e}")

        logging.info(f"[API] Found {len(databases)} similarity databases")
        return DatabaseListResponse(databases=databases, total=len(databases))

    except Exception as e:
        logging.error(f"[API] Error listing databases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list databases") from e


@router.post("/upload-file")
async def upload_amendment_file(
    file: UploadFile,
    metadata: Annotated[str, Form()],
) -> dict:
    """Upload an amendment file for database building.

    The file is stored temporarily and will be used when building the database.
    Returns the upload ID that should be included in the build request.

    Args:
        file: The amendment file to upload
        metadata: JSON string with required default_processing_timestamp and origin_project

    Returns:
        dict: Upload information including upload_id, filename, size, and metadata

    Raises:
        HTTPException: 500 if upload fails
    """
    try:
        # Parse metadata
        file_metadata = json.loads(metadata)

        # Generate unique upload ID
        upload_id = create_job_id()

        # Save file to temporary location
        temp_dir = Path("tmp/db_builder_uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)

        file_path = temp_dir / f"{upload_id}_{file.filename}"

        # Write file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        logging.info(
            f"[API] File uploaded successfully: {file.filename} (upload_id: {upload_id})"
        )

        return {
            "upload_id": upload_id,
            "filename": file.filename or "",
            "size": len(contents),
            "metadata": file_metadata,
        }
    except Exception as e:
        logging.error(f"[API] Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file") from e


@router.post("/build", response_model=ProcessingResponse)
async def build_database(request: DatabaseBuildRequest):
    """Start building a similarity database in the background.

    Args:
        request: DatabaseBuildRequest with build configuration

    Returns:
        ProcessingResponse: Job information for tracking build progress

    Raises:
        HTTPException: 400 for validation errors, 500 for build errors

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
            files_metadata = [ref.model_dump() for ref in request.file_references]
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
                )
            )
            logging.info(f"[API] Background task created successfully: {task}")
        except Exception as e:
            logging.error(f"[API] Error creating background task: {e}", exc_info=True)
            raise

        # Add callback to log task completion or errors
        def _log_task_result(task_future):
            try:
                task_future.result()
                logging.info(
                    f"[API] Background task completed successfully for job {job_id}"
                )
            except Exception as e:
                logging.error(
                    f"[API] Background task failed for job {job_id}: {e}", exc_info=True
                )

        task.add_done_callback(_log_task_result)

        logging.info(
            f"[API] Database build job started successfully - job_id: {job_id}, database: {request.database_name}"
        )
        return ProcessingResponse(
            job_id=job_id, status=JobStatus.queued, message="Database build job started"
        )

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

    Args:
        upload_id: The upload ID of the file to delete

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if upload not found, 500 if deletion fails
    """
    try:
        temp_upload_dir = Path("tmp/db_builder_uploads")

        # Find file with this upload_id
        for file_path in temp_upload_dir.glob(f"{upload_id}_*"):
            file_path.unlink()
            logging.info(f"[API] Deleted uploaded file: {file_path}")
            return {"message": "File deleted successfully"}

        raise HTTPException(status_code=404, detail="Upload not found")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Error deleting uploaded file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete file") from e
