"""
User management API routes.

This module provides endpoints for user profile and admin user management,
including listing users and toggling admin status.
"""

import logging
import logging.config
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from graal.api.models.responses import UserResponse
from graal.api.services.authorization_service import get_authorization_service
from graal.database.base import get_async_session_maker
from graal.database.models import User

logging.config.fileConfig("logging.conf")


router = APIRouter(tags=["users"])


class UserListResponse(BaseModel):
    """Response model for paginated user list."""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of users per page")


class ToggleAdminRequest(BaseModel):
    """Request model for toggling admin status."""

    is_admin: bool = Field(..., description="New admin status")


@router.get("/users/me", response_model=UserResponse)
async def get_my_profile(
    request: Request, session: Optional[str] = Cookie(default=None)
):
    """
    Get current user's profile.

    This endpoint returns the full profile of the authenticated user,
    including their admin status.

    Args:
        request: FastAPI request object
        session: Session cookie value

    Returns:
        UserResponse with user profile

    Raises:
        HTTPException: 401 if not authenticated
    """
    logging.info("[API] Getting user profile")

    try:
        auth_service = get_authorization_service()
        user = await auth_service.get_current_user(request, session)
        logging.info(f"[API] Profile retrieved for user {user.user_id}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to retrieve profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve user profile"
        ) from e


@router.get("/admin/users", response_model=UserListResponse)
async def list_users(
    request: Request,
    session: Optional[str] = Cookie(default=None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Users per page"),
):
    """
    List all users (admin only).

    This endpoint returns a paginated list of all users in the system.
    Only accessible by administrators.

    Args:
        request: FastAPI request object
        session: Session cookie value
        page: Page number (1-indexed)
        page_size: Number of users per page (max 100)

    Returns:
        UserListResponse with paginated user list

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
    """
    logging.info(f"[API] Listing users (page={page}, page_size={page_size})")

    try:
        # Check admin access
        auth_service = get_authorization_service()
        await auth_service.require_admin(request, session)

        # Query users from database
        session_maker = get_async_session_maker()
        async with session_maker() as db_session:
            # Count total users
            count_result = await db_session.execute(select(User))
            all_users = count_result.scalars().all()
            total = len(all_users)

            # Get paginated users
            offset = (page - 1) * page_size
            result = await db_session.execute(
                select(User).offset(offset).limit(page_size)
            )
            users = result.scalars().all()

            # Convert to response models
            user_responses = [
                UserResponse(
                    user_id=str(user.id),
                    email=user.email,
                    is_admin=user.is_admin,
                )
                for user in users
            ]

            logging.info(f"[API] Retrieved {len(user_responses)} users (total={total})")
            return UserListResponse(
                users=user_responses,
                total=total,
                page=page,
                page_size=page_size,
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to list users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users") from e


@router.patch("/admin/users/{user_id}/admin", response_model=UserResponse)
async def toggle_admin_status(
    user_id: UUID,
    toggle_request: ToggleAdminRequest,
    request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """
    Toggle admin status for a user (admin only).

    This endpoint allows administrators to grant or revoke admin privileges
    for other users. Administrators cannot remove their own admin status.

    Args:
        user_id: UUID of the user to modify
        toggle_request: Request body with new admin status
        request: FastAPI request object
        session: Session cookie value

    Returns:
        UserResponse with updated user information

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin or trying to modify own status
        HTTPException: 404 if user not found
    """
    logging.info(f"[API] Toggling admin status for user {user_id}")

    try:
        # Check admin access
        auth_service = get_authorization_service()
        current_user = await auth_service.require_admin(request, session)

        # Prevent self-modification
        if str(user_id) == current_user.user_id:
            logging.warning(
                f"[API] User {current_user.user_id} attempted to modify own admin status"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot modify your own admin status",
            )

        # Update user in database
        session_maker = get_async_session_maker()
        async with session_maker() as db_session:
            result = await db_session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                logging.warning(f"[API] User {user_id} not found")
                raise HTTPException(status_code=404, detail="User not found")

            # Update admin status
            old_status = user.is_admin
            user.is_admin = toggle_request.is_admin
            await db_session.commit()
            await db_session.refresh(user)

            logging.info(
                f"[API] User {user_id} admin status changed: {old_status} -> {user.is_admin}"
            )

            return UserResponse(
                user_id=str(user.id),
                email=user.email,
                is_admin=user.is_admin,
            )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to toggle admin status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update admin status"
        ) from e
