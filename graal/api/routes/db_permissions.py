"""
Database Permissions API

Provides endpoints for:
- Listing all permissions for a DB
- Assigning a role to a user by email (owner-only)
- Removing a user's role (owner-only)
- Listing databases user can manage
"""

import logging
import logging.config
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from graal.api.dependencies.auth import CurrentUser
from graal.api.models.requests import AssignPermissionRequest
from graal.api.models.responses import (
    DatabasePermissionResponse,
    ManagedDatabaseResponse,
    UserResponse,
)
from graal.api.services.database_permission_service import (
    DbRole,
    get_database_permission_service,
)
from graal.api.services.similarity_db_manifest_service import (
    get_similarity_db_manifest_service,
)

logging.config.fileConfig("logging.conf")
router = APIRouter(prefix="/databases", tags=["Database Permissions"])


@router.get("/users/search", response_model=list[UserResponse])
async def search_users_by_email(
    email: str,
    current_user: CurrentUser,
):
    """Search for users by email (partial match).

    Used for autocomplete/search when assigning permissions.
    Only returns users whose email contains the search term.

    Args:
        email: Email search term (partial match)
        current_user: Authenticated user (injected by FastAPI)

    Returns:
        List of UserResponse matching the search term (max 10 results)

    Raises:
        HTTPException: 401 if not authenticated
    """
    logging.info(f"[API] Searching users by email: {email}")

    try:
        from sqlalchemy import select

        from graal.database.base import get_async_session_maker
        from graal.database.models import User

        async with get_async_session_maker()() as session:
            result = await session.execute(
                select(User)
                .where(
                    User.email.ilike(f"%{email}%"),
                    User.id != current_user.user_id,  # Exclude current user
                )
                .limit(10)
            )
            users = result.scalars().all()
        user_responses = [
            UserResponse(
                user_id=str(user.id),
                email=user.email,
                is_admin=user.is_admin,
            )
            for user in users
        ]

        logging.info(f"[API] Found {len(user_responses)} users matching '{email}'")
        return user_responses

    except Exception as e:
        logging.error(f"[API] Error searching users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search users") from e


@router.get("/managed", response_model=list[ManagedDatabaseResponse])
async def list_managed_databases(current_user: CurrentUser):
    """List databases that user can manage (owns or is admin).

    Owners see only databases they own.
    Admins see all active databases.

    Args:
        current_user: Authenticated user (injected by FastAPI)

    Returns:
        List of ManagedDatabaseResponse with database info and user role

    Raises:
        HTTPException: 401 if not authenticated
    """
    logging.info(f"[API] Listing managed databases for user {current_user.user_id}")

    try:
        perm_service = get_database_permission_service()
        manifest_service = get_similarity_db_manifest_service()

        if current_user.is_admin:
            # Admins see all active databases
            manifests = await manifest_service.list_active_manifests()
            managed_databases = [
                ManagedDatabaseResponse(
                    id=str(manifest.id),
                    name=manifest.name,
                    size_bytes=manifest.size_bytes,
                    row_count=manifest.row_count,
                    last_modified=manifest.last_modified,
                    created_at=manifest.created_at,
                    user_role=None,  # Admins don't have explicit role
                )
                for manifest in manifests
            ]
        else:
            # Regular users see only databases they own
            manifests = await perm_service.list_databases_with_owner_role(
                current_user.user_id
            )
            managed_databases = [
                ManagedDatabaseResponse(
                    id=str(manifest.id),
                    name=manifest.name,
                    size_bytes=manifest.size_bytes,
                    row_count=manifest.row_count,
                    last_modified=manifest.last_modified,
                    created_at=manifest.created_at,
                    user_role="owner",
                )
                for manifest in manifests
            ]

        logging.info(
            f"[API] Found {len(managed_databases)} managed databases for user {current_user.user_id}"
        )
        return managed_databases

    except Exception as e:
        logging.error(f"[API] Error listing managed databases: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to list managed databases"
        ) from e


@router.get("/{db_id}/permissions", response_model=list[DatabasePermissionResponse])
async def list_db_permissions(
    db_id: UUID,
    current_user: CurrentUser,
):
    """List all permission entries for a database.

    Only database owners and admins can view permissions.

    Args:
        db_id: Database UUID
        current_user: Authenticated user (injected by FastAPI)

    Returns:
        List of DatabasePermissionResponse with user email and role

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not owner or admin
    """
    logging.info(
        f"[API] Listing permissions for database {db_id} (user: {current_user.user_id})"
    )

    try:
        perm_service = get_database_permission_service()

        # Check if user is owner or admin
        if not current_user.is_admin:
            user_role = await perm_service.get_user_role(
                str(db_id), current_user.user_id
            )
            if user_role != DbRole.owner:
                logging.warning(
                    f"[API] User {current_user.user_id} attempted to view permissions for DB {db_id} without owner role"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Only database owners can view permissions",
                )

        # Get all permissions for this database
        perms = await perm_service.list_roles_for_db(str(db_id))

        # Fetch user emails for each permission
        responses = []
        for perm in perms:
            # Get user from database to fetch email
            from sqlalchemy import select

            from graal.database.base import get_async_session_maker
            from graal.database.models import User

            async with get_async_session_maker()() as session:
                result = await session.execute(
                    select(User).where(User.id == perm.user_id)
                )
                user = result.scalar_one_or_none()

            responses.append(
                DatabasePermissionResponse(
                    db_id=str(perm.db_id),
                    user_id=str(perm.user_id),
                    email=user.email if user else "unknown",
                    role=perm.role.value,
                    created_at=perm.created_at,
                )
            )

        logging.info(f"[API] Retrieved {len(responses)} permissions for DB {db_id}")
        return responses

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Error listing permissions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to list database permissions"
        ) from e


@router.post(
    "/{db_id}/permissions",
    response_model=DatabasePermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_db_permission(
    db_id: UUID,
    request: AssignPermissionRequest,
    current_user: CurrentUser,
):
    """Assign a role to a user for a database by user ID.

    Only database owners and admins can assign permissions.
    Validates that the user ID exists in the system before assigning.

    Args:
        db_id: Database UUID
        request: Request with user_id and role
        current_user: Authenticated user (injected by FastAPI)

    Returns:
        DatabasePermissionResponse with assigned permission details

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not owner or admin
        HTTPException: 404 if user not found
        HTTPException: 400 if cannot demote last owner
    """
    logging.info(
        f"[API] Assigning {request.role} role to user {request.user_id} for DB {db_id} (by user: {current_user.user_id})"
    )

    try:
        perm_service = get_database_permission_service()

        # Check if user is owner or admin
        if not current_user.is_admin:
            user_role = await perm_service.get_user_role(
                str(db_id), current_user.user_id
            )
            if user_role != DbRole.owner:
                logging.warning(
                    f"[API] User {current_user.user_id} attempted to assign permission for DB {db_id} without owner role"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Only database owners can assign permissions",
                )

        # Look up user by ID to get their email and validate they exist
        from sqlalchemy import select

        from graal.database.base import get_async_session_maker
        from graal.database.models import User

        async with get_async_session_maker()() as session:
            result = await session.execute(
                select(User).where(User.id == request.user_id)
            )
            target_user = result.scalar_one_or_none()

        if not target_user:
            logging.warning(
                f"[API] User not found with ID {request.user_id} when assigning permission"
            )
            raise HTTPException(
                status_code=404,
                detail=f"No user found with ID: {request.user_id}",
            )

        # Assign the role
        await perm_service.set_user_role(str(db_id), str(target_user.id), request.role)

        logging.info(
            f"[API] Assigned {request.role} role to user {target_user.id} for DB {db_id}"
        )

        # Return the created permission
        from datetime import datetime, timezone

        return DatabasePermissionResponse(
            db_id=str(db_id),
            user_id=str(target_user.id),
            email=target_user.email,
            role=request.role,
            created_at=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logging.warning(f"[API] Validation error assigning permission: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.error(f"[API] Error assigning permission: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to assign database permission"
        ) from e


@router.delete(
    "/{db_id}/permissions/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_db_permission(
    db_id: UUID,
    target_user_id: UUID,
    current_user: CurrentUser,
):
    """Remove a user's role for a database.

    Only database owners and admins can remove permissions.
    Cannot remove the last owner.

    Args:
        db_id: Database UUID
        target_user_id: User UUID whose permission to remove
        current_user: Authenticated user (injected by FastAPI)

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not owner or admin
        HTTPException: 400 if cannot remove last owner
    """
    logging.info(
        f"[API] Removing permission for user {target_user_id} from DB {db_id} (by user: {current_user.user_id})"
    )

    try:
        perm_service = get_database_permission_service()

        # Check if user is owner or admin
        if not current_user.is_admin:
            user_role = await perm_service.get_user_role(
                str(db_id), current_user.user_id
            )
            if user_role != DbRole.owner:
                logging.warning(
                    f"[API] User {current_user.user_id} attempted to remove permission for DB {db_id} without owner role"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Only database owners can remove permissions",
                )

        # Remove the role
        await perm_service.remove_user_role(str(db_id), str(target_user_id))

        logging.info(
            f"[API] Removed permission for user {target_user_id} from DB {db_id}"
        )
        return None

    except HTTPException:
        raise
    except ValueError as e:
        logging.warning(f"[API] Validation error removing permission: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logging.error(f"[API] Error removing permission: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to remove database permission"
        ) from e
