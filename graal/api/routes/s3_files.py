"""API routes for S3 file management (admin-only)."""

import logging
import logging.config
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path

from graal.api.dependencies.auth import require_admin
from graal.api.models.responses import (
    S3DeleteResponse,
    S3FileListResponse,
    S3FileMetadata,
)
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.utils.s3.s3_service import get_s3_service

logging.config.fileConfig("logging.conf")
router = APIRouter(
    prefix="/admin/s3",
    tags=["s3-files"],
    dependencies=[Depends(require_admin)],  # Applied to all routes
)


_POOL_HASH_RE = re.compile(r"(?P<hash>[0-9a-f]{64})")


def _extract_file_hash_from_pool_key(pool_key: str) -> str | None:
    """Extract SHA256 hash from a pool key.

    Pool keys are content-addressed (hash-based), typically:
    "input_files/pool/{hash}.{ext}" in S3; the API returns the relative key.

    Args:
        pool_key: Relative pool key returned by InputPoolS3Service.

    Returns:
        The 64-hex SHA256 hash if present, else None.
    """

    match = _POOL_HASH_RE.search(pool_key)
    return match.group("hash") if match else None


def _pick_display_name(
    filename_to_latest_uploaded_at: dict[str, datetime],
) -> str | None:
    """Pick the best display filename from a set of candidates.

    Prefer the filename associated with the most recent uploaded_at.
    """

    if not filename_to_latest_uploaded_at:
        return None

    latest_filename, _ = max(
        filename_to_latest_uploaded_at.items(),
        key=lambda kv: kv[1],
    )
    return latest_filename


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
async def list_input_pool_files():  # noqa: C901
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

        # Build an enrichment index from Postgres manifests.
        # NOTE: This endpoint is admin-only, and we intentionally do NOT read per-object S3 metadata.
        manifest_service = get_similarity_db_manifest_service()
        # Admin view: include inactive manifests so we can still resolve filenames
        # for pool files that were used in the past.
        manifests = await manifest_service.list_all_manifests()

        # Index by file_hash.
        # - filename_to_latest_uploaded_at: for choosing display_name
        # - known_filenames: for modal
        # - referenced_by_databases: for modal
        filename_to_latest_uploaded_at_by_hash: dict[str, dict[str, datetime]] = (
            defaultdict(dict)
        )
        known_filenames_by_hash: dict[str, set[str]] = defaultdict(set)
        db_refs_by_hash: dict[str, dict[str, str]] = defaultdict(dict)

        for manifest in manifests:
            input_files = manifest.input_files or {}
            files = input_files.get("files")
            if not isinstance(files, list):
                continue

            for file_data in files:
                if not isinstance(file_data, dict):
                    continue

                file_hash = file_data.get("file_hash")
                filename = file_data.get("filename")
                uploaded_at_raw = file_data.get("uploaded_at")

                if not isinstance(file_hash, str) or not file_hash:
                    continue
                if not isinstance(filename, str) or not filename:
                    continue

                known_filenames_by_hash[file_hash].add(filename)
                db_refs_by_hash[file_hash][str(manifest.id)] = manifest.name

                uploaded_at: datetime
                if isinstance(uploaded_at_raw, str) and uploaded_at_raw:
                    try:
                        uploaded_at = datetime.fromisoformat(
                            uploaded_at_raw.replace("Z", "+00:00")
                        )
                    except ValueError:
                        uploaded_at = datetime.min
                else:
                    uploaded_at = datetime.min

                current_latest = filename_to_latest_uploaded_at_by_hash[file_hash].get(
                    filename
                )
                if current_latest is None or uploaded_at > current_latest:
                    filename_to_latest_uploaded_at_by_hash[file_hash][filename] = (
                        uploaded_at
                    )

        files = [
            S3FileMetadata(
                key=file["key"],
                size=file["size"],
                last_modified=file["last_modified"],
                file_type=file["file_type"],
                **_build_input_pool_enrichment(
                    file_key=file["key"],
                    filename_to_latest_uploaded_at_by_hash=filename_to_latest_uploaded_at_by_hash,
                    known_filenames_by_hash=known_filenames_by_hash,
                    db_refs_by_hash=db_refs_by_hash,
                ),
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


def _build_input_pool_enrichment(
    *,
    file_key: str,
    filename_to_latest_uploaded_at_by_hash: dict[str, dict[str, datetime]],
    known_filenames_by_hash: dict[str, set[str]],
    db_refs_by_hash: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Build optional UI enrichment fields for an input pool file.

    All enrichment comes from Postgres manifests.
    """

    file_hash = _extract_file_hash_from_pool_key(file_key)
    if not file_hash:
        return {}

    filename_to_latest_uploaded_at = filename_to_latest_uploaded_at_by_hash.get(
        file_hash, {}
    )
    display_name = _pick_display_name(filename_to_latest_uploaded_at)
    known_filenames = sorted(known_filenames_by_hash.get(file_hash, set()))
    referenced_by_databases = [
        {"id": db_id, "name": db_name}
        for db_id, db_name in sorted(
            db_refs_by_hash.get(file_hash, {}).items(), key=lambda kv: kv[1]
        )
    ]

    return {
        "file_hash": file_hash,
        "display_name": display_name,
        "known_filenames": known_filenames or None,
        "referenced_by_databases": referenced_by_databases or None,
    }


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
