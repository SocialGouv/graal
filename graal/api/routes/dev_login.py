"""
Development-only login routes.

SECURITY WARNING: These routes are ONLY for development and review environments.
They MUST NEVER be enabled in preprod or production.

Enable by setting the BACKEND_ENABLE_DEV_LOGIN=true environment variable.
"""

import logging
import logging.config
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graal.api.services.session_service import get_session_service
from graal.database.base import get_async_session_maker
from graal.database.models import User

logging.config.fileConfig("logging.conf")

router = APIRouter(tags=["dev-authentication"])

# Predefined dev user identifiers (stable across restarts)
DEV_ADMIN_SUB = "dev-login-admin-sub"
DEV_USER_SUB = "dev-login-user-sub"

DEV_ADMIN_EMAIL = "admin-dev@graal.gouv.fr"
DEV_USER_EMAIL = "user-dev@graal.gouv.fr"


def _require_backend_enable_dev_login() -> None:
    """Raise 404 if BACKEND_ENABLE_DEV_LOGIN is not set to 'true'."""
    if os.getenv("BACKEND_ENABLE_DEV_LOGIN", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/auth/dev-login")
async def dev_login(
    role: str = Query(..., description="Role to login as: 'admin' or 'user'"),
):
    """
    Development-only login endpoint.

    Creates a session for a predefined dev user (admin or regular user).

    SECURITY: Only available when BACKEND_ENABLE_DEV_LOGIN=true.
    NEVER set this in preprod or production.

    Args:
        role: Either 'admin' or 'user'

    Returns:
        RedirectResponse to frontend with session cookie set

    Raises:
        HTTPException: 404 if BACKEND_ENABLE_DEV_LOGIN is not set
        HTTPException: 400 if role is invalid
    """
    _require_backend_enable_dev_login()

    if role not in ("admin", "user"):
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Must be 'admin' or 'user'",
        )

    is_admin = role == "admin"
    proconnect_sub = DEV_ADMIN_SUB if is_admin else DEV_USER_SUB
    email = DEV_ADMIN_EMAIL if is_admin else DEV_USER_EMAIL

    logging.info(f"[DevLogin] Dev login requested for role={role}")

    # Create or update dev user in database
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        await _upsert_dev_user(
            session=session,
            proconnect_sub=proconnect_sub,
            email=email,
            is_admin=is_admin,
        )

    # Create session token
    session_service = get_session_service()
    session_token = session_service.create_session_token(proconnect_sub)

    # Get frontend URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Redirect to frontend with session cookie
    response = RedirectResponse(url=frontend_url)
    max_age = session_service.get_max_age()
    response.set_cookie(
        key="session",
        value=session_token,
        max_age=max_age,
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
        samesite="lax",
        path="/",
    )

    logging.info(f"[DevLogin] Dev session created for role={role}, email={email}")
    return response


async def _upsert_dev_user(
    session: AsyncSession,
    proconnect_sub: str,
    email: str,
    is_admin: bool,
) -> User:
    """Create or update a dev user in the database."""
    result = await session.execute(
        select(User).where(User.proconnect_sub == proconnect_sub)
    )
    user = result.scalar_one_or_none()

    if user:
        user.email = email
        user.is_admin = is_admin
    else:
        user = User(
            proconnect_sub=proconnect_sub,
            email=email,
            email_verified=True,
            is_admin=is_admin,
            proconnect_claims={
                "dev_login": True,
                "role": "admin" if is_admin else "user",
            },
        )
        session.add(user)

    await session.commit()
    await session.refresh(user)
    return user
