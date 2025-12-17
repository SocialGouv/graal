"""
Similarity Database Manifest API routes.

This module provides endpoints for managing similarity database manifests,
allowing admins to sync from S3, create, update, and deactivate manifests,
and users to list available databases.
"""

import logging
import logging.config
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from graal.api.dependencies.auth import AdminUser, CurrentUser
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)
from graal.database.schemas import (
    SimilarityDBManifestCreate,
    SimilarityDBManifestRead,
    SimilarityDBManifestUpdate,
)

logging.config.fileConfig("logging.conf")


router = APIRouter(tags=["Similarity Databases"])


@router.get("/similarity-databases", response_model=list[SimilarityDBManifestRead])
async def list_similarity_databases(current_user: CurrentUser):
    """
    List all active similarity database manifests.

    Available to all authenticated users.

    Args:
        current_user: Authenticated user (injected by FastAPI)

    Returns:
        List of SimilarityDBManifestRead schemas

    Raises:
        HTTPException: 401 if not authenticated
    """
    logging.info(
        f"[API] Listing active similarity database manifests for user {current_user.user_id}"
    )

    try:
        manifest_service = get_similarity_db_manifest_service()

        # Admins see all active manifests
        if current_user.is_admin:
            manifests = await manifest_service.list_active_manifests()
        else:
            # Non-admins see only manifests they have explicit permissions for
            manifests = await manifest_service.list_accessible_manifests(
                UUID(current_user.user_id)
            )

        logging.info(f"[API] Retrieved {len(manifests)} permitted active manifests")
        return [SimilarityDBManifestRead.model_validate(m) for m in manifests]

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to list manifests: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list similarity database manifests"
        ) from e


@router.post(
    "/admin/similarity-databases",
    response_model=SimilarityDBManifestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_manifest(
    manifest: SimilarityDBManifestCreate,
    admin_user: AdminUser,
):
    """
    Manually create a similarity database manifest (admin only).

    Validates that the S3 file exists before creating the manifest.

    Args:
        manifest: Manifest data to create
        admin_user: Authenticated admin user (injected by FastAPI)

    Returns:
        Created SimilarityDBManifestRead schema

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 400 if S3 file validation fails
    """
    logging.info(
        f"[API] Admin creating manifest '{manifest.name}' (user: {admin_user.user_id})"
    )

    try:
        # Create manifest
        manifest_service = get_similarity_db_manifest_service()
        user_id = UUID(admin_user.user_id)
        new_manifest = await manifest_service.create_manifest(manifest, user_id)

        logging.info(f"[API] Created manifest {new_manifest.id}")
        return SimilarityDBManifestRead.model_validate(new_manifest)

    except ValueError as e:
        logging.warning(f"[API] Validation error creating manifest: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to create manifest: {e}")
        raise HTTPException(status_code=500, detail="Failed to create manifest") from e


@router.patch(
    "/admin/similarity-databases/{manifest_id}",
    response_model=SimilarityDBManifestRead,
)
async def update_manifest(
    manifest_id: UUID,
    updates: SimilarityDBManifestUpdate,
    admin_user: AdminUser,
):
    """
    Update a similarity database manifest (admin only).

    Allows updating manifest metadata such as name, size, row count,
    and custom metadata.

    Args:
        manifest_id: Manifest UUID to update
        updates: Fields to update
        admin_user: Authenticated admin user (injected by FastAPI)

    Returns:
        Updated SimilarityDBManifestRead schema

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if manifest not found
    """
    logging.info(
        f"[API] Admin updating manifest {manifest_id} (user: {admin_user.user_id})"
    )

    try:
        # Update manifest
        manifest_service = get_similarity_db_manifest_service()
        updated_manifest = await manifest_service.update_manifest(manifest_id, updates)

        logging.info(f"[API] Updated manifest {manifest_id}")
        return SimilarityDBManifestRead.model_validate(updated_manifest)

    except ValueError as e:
        logging.warning(f"[API] Validation error updating manifest: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Manifest not found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to update manifest: {e}")
        raise HTTPException(status_code=500, detail="Failed to update manifest") from e


@router.delete(
    "/admin/similarity-databases/{manifest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_manifest(
    manifest_id: UUID,
    admin_user: AdminUser,
):
    """
    Deactivate a similarity database manifest (admin only, soft delete).

    Sets the manifest's is_active flag to False. The manifest and its
    metadata remain in the database but won't appear in active listings.

    Args:
        manifest_id: Manifest UUID to deactivate
        admin_user: Authenticated admin user (injected by FastAPI)

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if manifest not found
    """
    logging.info(
        f"[API] Admin deactivating manifest {manifest_id} (user: {admin_user.user_id})"
    )

    try:
        # Deactivate manifest
        manifest_service = get_similarity_db_manifest_service()
        await manifest_service.deactivate_manifest(manifest_id)

        logging.info(f"[API] Deactivated manifest {manifest_id}")
        return None

    except ValueError as e:
        logging.warning(f"[API] Error deactivating manifest: {e}")
        raise HTTPException(status_code=404, detail="Manifest not found") from e
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to deactivate manifest: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to deactivate manifest"
        ) from e


@router.delete(
    "/admin/similarity-databases/{manifest_id}/with-file",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_manifest_with_file(
    manifest_id: UUID,
    _admin_user: AdminUser,
):
    """Delete a similarity database and its manifest by ID (admin only).

    This endpoint is the canonical way for admins to delete an amendment
    database: it removes the underlying S3 parquet file *and* deactivates or
    deletes the corresponding manifest, ensuring consistency between S3 and
    Postgres.

    Args:
        manifest_id: Manifest UUID identifying the database to delete
        request: FastAPI request object
        session: Session cookie value

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if manifest not found
    """
    logging.info(
        f"[API] Admin deleting database (with file) for manifest {manifest_id}"
    )

    try:
        manifest_service = get_similarity_db_manifest_service()
        await manifest_service.delete_database_by_id(manifest_id)

        logging.info(
            f"[API] Deleted database and deactivated manifest {manifest_id} (with file)"
        )
        return None

    except ValueError as e:
        logging.warning(f"[API] Error deleting database with file: {e}")
        raise HTTPException(status_code=404, detail="Manifest not found") from e
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensive logging
        logging.error(f"[API] Failed to delete database with file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete similarity database and its file",
        ) from e
