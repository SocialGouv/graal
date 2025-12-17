"""
Authentication and authorization dependencies for FastAPI routes.

This module provides dependency functions that can be injected into route handlers
to enforce authentication and authorization requirements. Using FastAPI's Depends()
mechanism makes auth requirements explicit and reduces boilerplate code.

Usage:
    @router.get("/protected")
    async def protected_endpoint(current_user: CurrentUser):
        # current_user is guaranteed to be authenticated
        pass

    @router.post("/admin/sensitive")
    async def admin_endpoint(admin_user: AdminUser):
        # admin_user is guaranteed to be an admin
        pass
"""

import logging
import logging.config
from typing import Annotated, Optional

from fastapi import Cookie, Depends, Request

from graal.api.models.responses import UserResponse
from graal.api.services.authorization_service import get_authorization_service

logging.config.fileConfig("logging.conf")


async def get_current_user(
    request: Request, session: Optional[str] = Cookie(default=None)
) -> UserResponse:
    """FastAPI dependency that enforces authentication.

    This dependency validates the session cookie and retrieves the current user.
    If the user is not authenticated, it raises HTTPException(401).

    Args:
        request: FastAPI request object (automatically injected)
        session: Session cookie value (automatically injected)

    Returns:
        UserResponse: The authenticated user

    Raises:
        HTTPException: 401 if not authenticated or session invalid

    Example:
        @router.get("/protected")
        async def protected_route(current_user: CurrentUser):
            # current_user is guaranteed to be authenticated
            return {"user_id": current_user.user_id}
    """
    auth_service = get_authorization_service()
    user = await auth_service.get_current_user(request, session)
    logging.debug(f"[AuthDependency] Authenticated user: {user.user_id}")
    return user


async def require_admin(
    request: Request, session: Optional[str] = Cookie(default=None)
) -> UserResponse:
    """FastAPI dependency that enforces admin access.

    This dependency validates the session cookie, retrieves the current user,
    and verifies they have admin privileges. If the user is not an admin,
    it raises HTTPException(403).

    Args:
        request: FastAPI request object (automatically injected)
        session: Session cookie value (automatically injected)

    Returns:
        UserResponse: The authenticated admin user

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin

    Example:
        @router.post("/admin/sensitive")
        async def admin_only_route(admin_user: AdminUser):
            # admin_user is guaranteed to be an admin
            return {"message": "Admin operation successful"}
    """
    auth_service = get_authorization_service()
    user = await auth_service.require_admin(request, session)
    logging.debug(f"[AuthDependency] Admin access granted: {user.user_id}")
    return user


# Type aliases for cleaner route signatures
# These use Annotated to combine the type hint with the dependency
CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
"""Type alias for authenticated user dependency.

Use this in route parameters to enforce authentication:
    async def my_route(current_user: CurrentUser):
        ...
"""

AdminUser = Annotated[UserResponse, Depends(require_admin)]
"""Type alias for admin user dependency.

Use this in route parameters to enforce admin access:
    async def my_admin_route(admin_user: AdminUser):
        ...
"""
