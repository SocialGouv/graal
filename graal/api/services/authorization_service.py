"""
Authorization service for user authentication and admin access control.

This module provides a pluggable authorization system following SOLID principles:
- Abstract provider interface for extensibility
- Hardcoded provider for MVP (to be replaced with database provider)
- Singleton service for centralized authorization logic

Migration Path:
    When database is ready, replace HardcodedAuthorizationProvider with
    DatabaseAuthorizationProvider that queries user permissions from database.
"""

import logging
import logging.config
from abc import ABC, abstractmethod
from typing import Optional

from fastapi import Cookie, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.api.models.responses import UserResponse
from graal.api.services.database_permission_service import (
    get_database_permission_service,
)
from graal.database.models import User

logging.config.fileConfig("logging.conf")


class AuthorizationProvider(ABC):
    """Abstract interface for authorization providers.

    This interface follows SOLID principles (Interface Segregation) by defining
    a minimal, focused contract for authorization operations. Implementations
    can use different backends (hardcoded, database, LDAP, etc.).
    """

    @abstractmethod
    async def get_user(self, proconnect_sub: str) -> Optional[UserResponse]:
        """Retrieve user information by ProConnect subject identifier.

        Args:
            proconnect_sub: ProConnect subject identifier (unique user ID)

        Returns:
            UserResponse object if found, None otherwise
        """
        pass


class HardcodedAuthorizationProvider(AuthorizationProvider):
    """Hardcoded authorization provider for MVP.

    This provider always returns admin access for any user. It serves as
    a temporary implementation until database-backed authorization is ready.

    Migration Notes:
        - Replace this class with DatabaseAuthorizationProvider
        - Update get_authorization_service() to use new provider
        - All TODO markers below indicate code that needs database queries
    """

    async def get_user(self, proconnect_sub: str) -> Optional[UserResponse]:
        """Return hardcoded admin user.

        TODO: DATABASE MIGRATION
        Replace with actual database query:
            async with db_session() as session:
                user_record = await session.execute(
                    select(UserModel).where(UserModel.proconnect_sub == proconnect_sub)
                )
                return user_record.scalar_one_or_none()

        Args:
            proconnect_sub: ProConnect subject identifier (currently ignored)

        Returns:
            Hardcoded admin UserResponse
        """
        logging.debug(
            f"[HardcodedAuthProvider] Returning hardcoded admin user for sub: {proconnect_sub}"
        )
        return UserResponse(
            user_id="hardcoded-admin",
            email="admin@graal.gouv.fr",
            is_admin=True,
        )


class DatabaseAuthorizationProvider(AuthorizationProvider):
    """Database-backed authorization provider.

    This provider queries the User table to retrieve user information
    based on their ProConnect subject identifier. It replaces the
    HardcodedAuthorizationProvider for production use.

    Attributes:
        _session_factory: Async session factory for database queries
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize database authorization provider.

        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory
        logging.info("[DatabaseAuthProvider] Initialized with database session factory")

    async def get_user(self, proconnect_sub: str) -> Optional[UserResponse]:
        """Retrieve user from database by ProConnect subject identifier.

        Args:
            proconnect_sub: ProConnect subject identifier

        Returns:
            UserResponse if user found, None otherwise
        """
        logging.debug(
            f"[DatabaseAuthProvider] Querying user by proconnect_sub={proconnect_sub[:8]}..."
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(User).where(User.proconnect_sub == proconnect_sub)
            )
            user = result.scalar_one_or_none()

            if not user:
                logging.debug(
                    f"[DatabaseAuthProvider] User not found for sub={proconnect_sub[:8]}..."
                )
                return None

            logging.info(
                f"[DatabaseAuthProvider] User {user.id} found (admin={user.is_admin})"
            )
            return UserResponse(
                user_id=str(user.id),
                email=user.email,
                is_admin=user.is_admin,
            )


class DbRole:
    reader = "reader"
    writer = "writer"
    owner = "owner"

    RANK = {
        reader: 1,
        writer: 2,
        owner: 3,
    }


class AuthorizationService:
    """Main authorization service for user authentication and access control.

    This service follows SOLID principles:
    - Single Responsibility: Handles only authorization logic
    - Dependency Inversion: Depends on abstract AuthorizationProvider interface

    The service delegates actual authorization logic to the injected provider,
    making it easy to swap implementations without changing the service code.

    Attributes:
        _provider: Authorization provider implementation
    """

    def __init__(self, provider: AuthorizationProvider):
        """Initialize authorization service with a provider.

        Args:
            provider: Authorization provider implementation
        """
        self._provider = provider
        logging.info(
            f"[AuthorizationService] Initialized with provider: {provider.__class__.__name__}"
        )

    async def get_current_user(
        self, _request: Request, session: Optional[str] = Cookie(default=None)
    ) -> UserResponse:
        """Get current authenticated user information from session cookie.

        This method extracts the session token from the HTTP-only cookie,
        validates it, and retrieves the user from the database.

        Args:
            request: FastAPI request object
            session: Session cookie value (automatically injected by FastAPI)

        Returns:
            Current authenticated UserResponse

        Raises:
            HTTPException: 401 if not authenticated or session invalid
        """
        # Import session service here to avoid circular imports
        from graal.api.services.session_service import get_session_service

        # Check if session cookie exists
        if not session:
            logging.debug("[AuthorizationService] No session cookie provided")
            raise HTTPException(
                status_code=401,
                detail="Not authenticated",
            )

        # Validate session token and get proconnect_sub
        session_service = get_session_service()
        proconnect_sub = session_service.validate_session_token(session)

        if not proconnect_sub:
            logging.warning("[AuthorizationService] Invalid or expired session token")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
            )

        logging.debug(
            f"[AuthorizationService] Session valid for proconnect_sub={proconnect_sub[:8]}..."
        )

        # Get user from provider (database)
        user = await self._provider.get_user(proconnect_sub)
        if not user:
            logging.error(
                f"[AuthorizationService] User not found for sub={proconnect_sub[:8]}..."
            )
            raise HTTPException(
                status_code=401,
                detail="User not found",
            )

        logging.info(
            f"[AuthorizationService] Retrieved user {user.user_id} (admin={user.is_admin})"
        )
        return user

    async def check_admin(
        self, request: Request, session: Optional[str] = Cookie(default=None)
    ) -> bool:
        """Check if current user has admin privileges.

        Args:
            request: FastAPI request object
            session: Session cookie value

        Returns:
            True if current user is admin, False otherwise
        """
        try:
            user = await self.get_current_user(request, session)
            logging.debug(
                f"[AuthorizationService] Admin check for {user.user_id}: {user.is_admin}"
            )
            return user.is_admin
        except HTTPException:
            return False

    async def require_admin(
        self, request: Request, session: Optional[str] = Cookie(default=None)
    ) -> UserResponse:
        """Require admin access, raise exception if not authorized.

        This method should be used in API endpoints that require admin access.
        It will raise an HTTP 403 Forbidden error if the user is not an admin.

        Args:
            request: FastAPI request object
            session: Session cookie value

        Returns:
            Current UserResponse if admin

        Raises:
            HTTPException: 401 if not authenticated
            HTTPException: 403 if not admin
        """
        user = await self.get_current_user(request, session)

        if not user.is_admin:
            logging.warning(
                f"[AuthorizationService] Access denied for non-admin user: {user.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        logging.info(
            f"[AuthorizationService] Admin access granted for user: {user.user_id}"
        )
        return user

    async def get_db_role(
        self,
        db_id: str,
        request: Request,
        session: Optional[str] = Cookie(default=None),
    ) -> str | None:
        """
        Return the user's role for a specific amendment database.
        """
        user = await self.get_current_user(request, session)

        perm_service = get_database_permission_service()
        return await perm_service.get_user_role(db_id, user.user_id)

    async def require_db_role(
        self,
        db_id: str,
        min_role: str,
        request: Request,
        session: Optional[str] = Cookie(default=None),
    ) -> UserResponse:
        """
        Require that the current user has at least the specified role for a DB.
        Raises HTTP 403 if insufficient permission.
        """
        user = await self.get_current_user(request, session)

        perm_service = get_database_permission_service()
        role = await perm_service.get_user_role(db_id, user.user_id)

        # No role at all
        if role is None:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions for this database",
            )

        # Hierarchical check
        if DbRole.RANK[role] < DbRole.RANK[min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"Requires {min_role} role on this database",
            )

        return user


# Singleton instance (following project pattern from other services)
_authorization_service: Optional[AuthorizationService] = None


def get_authorization_service(use_database: bool = True) -> AuthorizationService:
    """Get global authorization service instance (Singleton pattern).

    This function follows the project's service pattern for singleton instances.
    The service can be initialized with either DatabaseAuthorizationProvider
    (production) or HardcodedAuthorizationProvider (testing/development).

    Args:
        use_database: If True, use DatabaseAuthorizationProvider.
                     If False, use HardcodedAuthorizationProvider.
                     Default is True for production use.

    Returns:
        Global authorization service instance
    """
    global _authorization_service
    if _authorization_service is None:
        logging.info("[AuthorizationService] Initializing singleton instance")

        if use_database:
            # Production: Use database-backed authorization
            from graal.database.base import get_async_session_maker

            session_factory = get_async_session_maker()
            provider = DatabaseAuthorizationProvider(session_factory)
            logging.info("[AuthorizationService] Using DatabaseAuthorizationProvider")
        else:
            # Development/Testing: Use hardcoded authorization
            provider = HardcodedAuthorizationProvider()
            logging.info("[AuthorizationService] Using HardcodedAuthorizationProvider")

        _authorization_service = AuthorizationService(provider)
    return _authorization_service
