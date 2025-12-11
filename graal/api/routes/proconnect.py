"""
ProConnect OAuth authentication routes.

This module provides OAuth 2.0 / OpenID Connect authentication endpoints
for ProConnect integration, including login initiation, callback handling,
and logout functionality.
"""

import logging
import logging.config
import os

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from graal.api.services.proconnect_service import get_proconnect_service
from graal.api.services.session_service import get_session_service
from graal.database.base import get_async_session_maker
from graal.database.models import User

logging.config.fileConfig("logging.conf")

router = APIRouter(tags=["authentication"])

# In-memory storage for OAuth state and PKCE verifiers
# In production, this should be Redis or database-backed
_oauth_state_store: dict[str, dict[str, str]] = {}


@router.get("/auth/login")
async def login():
    """
    Initiate ProConnect OAuth login flow.

    This endpoint generates an authorization URL with state and PKCE parameters,
    stores them for validation, and redirects the user to ProConnect.

    Returns:
        RedirectResponse to ProConnect authorization endpoint

    Raises:
        HTTPException: 500 if OAuth initialization fails
    """
    logging.info("[API] ========== ProConnect login endpoint called ==========")

    try:
        logging.info("[API] Getting ProConnect service instance...")
        proconnect = get_proconnect_service()
        logging.info("[API] ProConnect service instance obtained successfully")

        # Generate authorization URL with state and PKCE
        logging.info("[API] Generating authorization URL...")
        auth_url, state, code_verifier = await proconnect.get_authorization_url()
        logging.info(
            f"[API] Authorization URL generated successfully with state={state[:8]}..."
        )

        # Store state and code_verifier for validation in callback
        # TODO: Use Redis or database for production (state should expire)
        _oauth_state_store[state] = {
            "code_verifier": code_verifier,
        }

        logging.info(f"[API] Redirecting to ProConnect with state={state[:8]}...")
        return RedirectResponse(url=auth_url)

    except ValueError as e:
        logging.error(f"[API] ProConnect configuration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Authentication service configuration error: {str(e)}",
        ) from e
    except Exception as e:
        logging.error(f"[API] Failed to initiate login: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate authentication: {str(e)}",
        ) from e


@router.get("/auth/callback")
async def callback(
    code: str,
    state: str,
):
    """
    Handle ProConnect OAuth callback.

    This endpoint:
    1. Validates the state parameter (CSRF protection)
    2. Exchanges authorization code for tokens
    3. Retrieves user claims from ProConnect
    4. Creates or updates user in database
    5. Creates session token
    6. Sets HTTP-only secure cookie
    7. Redirects to frontend

    Args:
        code: Authorization code from ProConnect
        state: State parameter for CSRF validation

    Returns:
        RedirectResponse to frontend with session cookie

    Raises:
        HTTPException: 400 if invalid state or code
        HTTPException: 500 if authentication fails
    """
    logging.info(f"[API] ProConnect callback received with state={state[:8]}...")

    try:
        # Validate state parameter
        stored_data = _oauth_state_store.get(state)
        if not stored_data:
            logging.warning(f"[API] Invalid or expired state: {state[:8]}...")
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired authentication request",
            )

        code_verifier = stored_data["code_verifier"]

        # Clean up used state
        del _oauth_state_store[state]

        # Exchange code for token
        proconnect = get_proconnect_service()
        logging.info("[API] Exchanging authorization code for token...")
        token = await proconnect.exchange_code_for_token(code, code_verifier)
        logging.info("[API] Token exchange successful")

        # Get user claims from token
        logging.info("[API] Extracting user claims from ID token...")
        claims = await proconnect.get_user_claims(token)
        logging.info(f"[API] Claims received: {list(claims.keys())}")
        logging.debug(f"[API] Full claims (debug): {claims}")

        # Extract required fields
        proconnect_sub = claims.get("sub")
        email = claims.get("email")
        email_verified = claims.get("email_verified", False)

        logging.info(
            f"[API] Extracted claims: sub={'SET' if proconnect_sub else 'MISSING'}, "
            f"email={'SET' if email else 'MISSING'}, "
            f"email_verified={email_verified}"
        )

        if not proconnect_sub or not email:
            logging.error(
                f"[API] Missing required claims. Available claims: {list(claims.keys())}. "
                f"sub={proconnect_sub}, email={email}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Invalid user information from authentication provider. "
                f"Missing required claims: {', '.join([c for c in ['sub', 'email'] if not claims.get(c)])}",
            )

        # Create or update user in database
        session_maker = get_async_session_maker()
        async with session_maker() as session:
            user = await _create_or_update_user(
                session=session,
                proconnect_sub=proconnect_sub,
                email=email,
                email_verified=email_verified,
                proconnect_claims=claims,
            )

        # Create session token
        session_service = get_session_service()
        session_token = session_service.create_session_token(proconnect_sub)

        # Get frontend URL from environment
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        # Create redirect response to frontend
        response = RedirectResponse(url=frontend_url)

        # Set HTTP-only secure cookie with session token
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

        logging.info(
            f"[API] User {user.id} authenticated successfully, redirecting to frontend"
        )
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logging.error(f"[API] Authentication failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed",
        ) from e
    except Exception as e:
        logging.error(f"[API] Unexpected error in callback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Authentication processing failed",
        ) from e


@router.post("/auth/logout")
async def logout(response: Response, session: str | None = Cookie(default=None)):
    """
    Logout current user by clearing session cookie.

    Args:
        response: FastAPI response object
        session: Session cookie value (optional)

    Returns:
        Success message
    """
    logging.info("[API] User logout requested")

    # Clear session cookie
    response.delete_cookie(
        key="session",
        path="/",
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
        samesite="lax",
    )

    logging.info("[API] User logged out successfully")
    return {"message": "Logged out successfully"}


async def _create_or_update_user(
    session: AsyncSession,
    proconnect_sub: str,
    email: str,
    email_verified: bool,
    proconnect_claims: dict,
) -> User:
    """
    Create or update user from ProConnect claims.

    This function queries the database for an existing user by proconnect_sub.
    If found, it updates the user's information. If not found, it creates a new user.

    Args:
        session: Async database session
        proconnect_sub: ProConnect subject identifier
        email: User email from ProConnect
        email_verified: Email verification status
        proconnect_claims: Full ProConnect claims for audit

    Returns:
        User model (created or updated)
    """
    # Query for existing user
    result = await session.execute(
        select(User).where(User.proconnect_sub == proconnect_sub)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        logging.info(f"[API] Updating existing user {user.id}")
        user.email = email
        user.email_verified = email_verified
        user.proconnect_claims = proconnect_claims
    else:
        # Create new user (not admin by default)
        logging.info(
            f"[API] Creating new user for proconnect_sub={proconnect_sub[:8]}..."
        )
        user = User(
            proconnect_sub=proconnect_sub,
            email=email,
            email_verified=email_verified,
            is_admin=False,  # New users are not admin by default
            proconnect_claims=proconnect_claims,
        )
        session.add(user)

    # Commit changes
    await session.commit()
    await session.refresh(user)

    logging.info(f"[API] User {user.id} provisioned successfully")
    return user
