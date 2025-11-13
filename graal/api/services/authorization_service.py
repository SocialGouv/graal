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

from graal.api.models.responses import UserResponse

logging.config.fileConfig("logging.conf")
logger = logging.getLogger(__name__)


class AuthorizationProvider(ABC):
    """Abstract interface for authorization providers.

    This interface follows SOLID principles (Interface Segregation) by defining
    a minimal, focused contract for authorization operations. Implementations
    can use different backends (hardcoded, database, LDAP, etc.).
    """

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Retrieve user information by user ID.

        Args:
            user_id: Unique identifier for the user

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

    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Return hardcoded admin user.

        TODO: DATABASE MIGRATION
        Replace with actual database query:
            async with db_session() as session:
                user_record = await session.execute(
                    select(UserModel).where(UserModel.user_id == user_id)
                )
                return user_record.scalar_one_or_none()

        Args:
            user_id: User identifier (currently ignored)

        Returns:
            Hardcoded admin UserResponse
        """
        logger.debug(
            f"[HardcodedAuthProvider] Returning hardcoded admin user for ID: {user_id}"
        )
        # TODO: Replace with database query
        return UserResponse(
            user_id="hardcoded-admin",
            email="admin@graal.gouv.fr",
            is_admin=True,
        )


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
        logger.info(
            f"[AuthorizationService] Initialized with provider: {provider.__class__.__name__}"
        )

    async def get_current_user(self) -> UserResponse:
        """Get current authenticated user information.

        TODO: DATABASE MIGRATION
        Replace hardcoded user_id extraction with actual session/JWT logic:
            - Extract user_id from request session
            - Or decode from JWT token
            - Or use FastAPI dependency injection with security scheme

        Returns:
            Current authenticated UserResponse

        Raises:
            ValueError: If user not found
        """
        # TODO: DATABASE MIGRATION - Get actual user_id from session/JWT
        user_id = "hardcoded-admin"
        logger.debug(f"[AuthorizationService] Getting current user: {user_id}")

        user = await self._provider.get_user(user_id)
        if not user:
            logger.error(f"[AuthorizationService] User not found: {user_id}")
            raise ValueError(f"User not found: {user_id}")

        logger.info(
            f"[AuthorizationService] Retrieved user {user.user_id} (admin={user.is_admin})"
        )
        return user

    async def check_admin(self) -> bool:
        """Check if current user has admin privileges.

        Returns:
            True if current user is admin, False otherwise
        """
        user = await self.get_current_user()
        logger.debug(
            f"[AuthorizationService] Admin check for {user.user_id}: {user.is_admin}"
        )
        return user.is_admin

    async def require_admin(self) -> UserResponse:
        """Require admin access, raise exception if not authorized.

        This method should be used in API endpoints that require admin access.
        It will raise an HTTP 403 Forbidden error if the user is not an admin.

        Returns:
            Current UserResponse if admin

        Raises:
            HTTPException: 403 Forbidden if user is not admin
        """
        user = await self.get_current_user()

        if not user.is_admin:
            logger.warning(
                f"[AuthorizationService] Access denied for non-admin user: {user.user_id}"
            )
            # Import here to avoid circular imports
            from fastapi import HTTPException

            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        logger.info(
            f"[AuthorizationService] Admin access granted for user: {user.user_id}"
        )
        return user


# Singleton instance (following project pattern from other services)
_authorization_service: Optional[AuthorizationService] = None


def get_authorization_service() -> AuthorizationService:
    """Get global authorization service instance (Singleton pattern).

    This function follows the project's service pattern for singleton instances.
    The service is initialized once with the HardcodedAuthorizationProvider
    and reused across all requests.

    Migration Note:
        When moving to database authentication, change the provider initialization:
        provider = DatabaseAuthorizationProvider(db_session_factory)

    Returns:
        Global authorization service instance
    """
    global _authorization_service
    if _authorization_service is None:
        logger.info("[AuthorizationService] Initializing singleton instance")
        # TODO: DATABASE MIGRATION - Replace with DatabaseAuthorizationProvider
        provider = HardcodedAuthorizationProvider()
        _authorization_service = AuthorizationService(provider)
    return _authorization_service
