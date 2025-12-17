"""API routes for S3 file management (admin-only)."""

import logging
import logging.config

from fastapi import APIRouter, Depends, HTTPException, Path

from graal.api.dependencies.auth import require_admin
from graal.api.models.responses import (
    S3DeleteResponse,
    S3FileListResponse,
    S3FileMetadata,
)
from graal.utils.s3.s3_service import get_s3_service

logging.config.fileConfig("logging.conf")
router = APIRouter(
    prefix="/admin/s3",
    tags=["s3-files"],
    dependencies=[Depends(require_admin)],  # Applied to all routes
)


@router.get("/config-files", response_model=S3FileListResponse)
async def list_config_files():
    """List all configuration files from S3.

    Admin-only endpoint to view all available config files.

    Args:
        admin_user: Authenticated admin user (injected by FastAPI)

    Returns:
        S3FileListResponse with list of config files and metadata

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin, 500 if S3 operation fails
    """

    try:
        s3_service = get_s3_service()
        files_metadata = await s3_service.config.list_config_files_with_metadata()

        files = [
            S3FileMetadata(
                key=file["key"],
                size=file["size"],
                last_modified=file["last_modified"],
                file_type=file["file_type"],
            )
            for file in files_metadata
        ]

        return S3FileListResponse(
            files=files,
            total_count=len(files),
            folder="config",
        )

    except Exception as e:
        logging.error(f"Failed to list config files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list configuration files: {str(e)}",
        ) from e


@router.delete("/config-files/{filename}", response_model=S3DeleteResponse)
async def delete_config_file(
    filename: str = Path(..., description="Configuration file name"),
):
    """Delete a configuration file from S3.

    Admin-only endpoint to delete config files.

    Args:
        filename: Name of the config file to delete

    Returns:
        S3DeleteResponse with deletion status

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin, 404 if file not found, 500 if deletion fails
    """

    try:
        s3_service = get_s3_service()
        await s3_service.config.delete_config_file(filename)

        logging.info(f"Admin deleted config file: {filename}")
        return S3DeleteResponse(
            success=True,
            message=f"Configuration file '{filename}' deleted successfully",
            deleted_file=filename,
        )

    except FileNotFoundError as e:
        logging.warning(f"Config file not found for deletion: {filename}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logging.error(f"Failed to delete config file {filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete configuration file: {str(e)}",
        ) from e


@router.get("/databases", response_model=S3FileListResponse)
async def list_database_files():
    """List all similarity database files from S3.

    Admin-only endpoint to view all available similarity databases.

    Returns:
        S3FileListResponse with list of database files and metadata

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin, 500 if S3 operation fails
    """

    try:
        s3_service = get_s3_service()
        files_metadata = await s3_service.database.list_database_files_with_metadata()

        files = [
            S3FileMetadata(
                key=file["key"],
                size=file["size"],
                last_modified=file["last_modified"],
                file_type=file["file_type"],
            )
            for file in files_metadata
        ]

        return S3FileListResponse(
            files=files,
            total_count=len(files),
            folder="database",
        )

    except Exception as e:
        logging.error(f"Failed to list database files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list database files: {str(e)}",
        ) from e


@router.delete("/databases/{database_name}", response_model=S3DeleteResponse)
async def delete_database_file(
    database_name: str = Path(
        ..., description="Database name (without .parquet extension)"
    ),
):
    """Delete a similarity database file from S3.

    Admin-only endpoint to delete database files.

    Args:
        database_name: Name of the database to delete (without .parquet extension)

    Returns:
        S3DeleteResponse with deletion status

    Raises:
        HTTPException: 403 if not admin, 404 if database not found, 500 if deletion fails
    """
    try:
        s3_service = get_s3_service()
        await s3_service.database.delete_database_file(database_name)

        logging.info(f"Admin deleted database: {database_name}")
        return S3DeleteResponse(
            success=True,
            message=f"Database '{database_name}' deleted successfully",
            deleted_file=database_name,
        )

    except FileNotFoundError as e:
        logging.warning(f"Database not found for deletion: {database_name}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logging.error(f"Failed to delete database {database_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete database: {str(e)}",
        ) from e


@router.get("/input-pool", response_model=S3FileListResponse)
async def list_input_pool_files():
    """List all files in the input pool from S3.

    Admin-only endpoint to view all uploaded files in the input pool.

    Returns:
        S3FileListResponse with list of input pool files and metadata

    Raises:
        HTTPException: 403 if not admin, 500 if S3 operation fails
    """

    try:
        s3_service = get_s3_service()
        files_metadata = await s3_service.pool.list_input_pool_files_with_metadata()

        files = [
            S3FileMetadata(
                key=file["key"],
                size=file["size"],
                last_modified=file["last_modified"],
                file_type=file["file_type"],
            )
            for file in files_metadata
        ]

        return S3FileListResponse(
            files=files,
            total_count=len(files),
            folder="input_pool",
        )

    except Exception as e:
        logging.error(f"Failed to list input pool files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list input pool files: {str(e)}",
        ) from e


@router.delete("/input-pool/{s3_key:path}", response_model=S3DeleteResponse)
async def delete_input_pool_file(
    s3_key: str = Path(..., description="S3 key of the file to delete"),
):
    """Delete a file from the input pool in S3.

    Admin-only endpoint to delete files from the input pool.

    Args:
        s3_key: S3 key (path) of the file to delete

    Returns:
        S3DeleteResponse with deletion status

    Raises:
        HTTPException: 403 if not admin, 404 if file not found, 500 if deletion fails
    """
    try:
        s3_service = get_s3_service()
        await s3_service.pool.delete_input_pool_file(s3_key)

        logging.info(f"Admin deleted input pool file: {s3_key}")
        return S3DeleteResponse(
            success=True,
            message=f"File '{s3_key}' deleted successfully from input pool",
            deleted_file=s3_key,
        )

    except FileNotFoundError as e:
        logging.warning(f"Input pool file not found for deletion: {s3_key}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logging.error(f"Failed to delete input pool file {s3_key}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file from input pool: {str(e)}",
        ) from e
