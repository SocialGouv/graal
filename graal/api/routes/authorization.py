"""
Authorization API routes.

Note: The /auth/me endpoint serves as the single source for both user information
and admin status checks. The is_admin field in the response indicates admin privileges.
"""

import logging
import logging.config
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Request

from graal.api.models.responses import UserResponse
from graal.api.services.authorization_service import get_authorization_service

logging.config.fileConfig("logging.conf")

router = APIRouter(tags=["authorization"])


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user(
    request: Request, session: Optional[str] = Cookie(default=None)
):
    """
    Get current authenticated user information, including admin status.

    This endpoint serves dual purposes:
    1. Retrieve user information (user_id, email)
    2. Check admin privileges via the is_admin field

    Frontend should use this single endpoint for all authentication checks.

    Returns:
        UserResponse with user details including admin status

    Raises:
        HTTPException: 500 if failed to retrieve user information
    """
    logging.info("[API] Getting current user information")

    try:
        auth_service = get_authorization_service()
        user = await auth_service.get_current_user(request, session)
        logging.info(
            f"[API] User {user.user_id} retrieved with admin status: {user.is_admin}"
        )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Unexpected error retrieving user: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve user information"
        ) from e
