"""
User Configuration Service for managing user-saved configuration presets.

This service provides CRUD operations for user configurations, allowing users
to save, load, and manage their preferred processing configurations.

Pattern:
    - Async/await throughout for all database operations
    - Singleton pattern via get_user_configuration_service()
    - Dependency injection of S3Service for validation
    - Transaction management with explicit commits and refreshes
"""

import logging
import logging.config
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.database.models import UserConfiguration
from graal.database.schemas import (
    UserConfigurationCreate,
    UserConfigurationUpdate,
)
from graal.utils.s3.s3_service import S3Service

logging.config.fileConfig("logging.conf")


class UserConfigurationService:
    """Service for managing user configuration presets.

    This service handles all CRUD operations for user configurations,
    including validation of S3 paths and management of default configurations.

    Attributes:
        _session_factory: Async session factory for database operations
        _s3_service: S3 service for validating configuration file paths
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        s3_service: S3Service,
    ):
        """Initialize user configuration service.

        Args:
            session_factory: SQLAlchemy async session factory
            s3_service: S3 service for file validation
        """
        self._session_factory = session_factory
        self._s3_service = s3_service
        logging.info("[UserConfigurationService] Initialized")

    async def create_configuration(
        self, user_id: UUID, config: UserConfigurationCreate
    ) -> UserConfiguration:
        """Create a new configuration for a user.

        Validates that the S3 config file exists before creating the configuration.
        If is_default is True, unsets all other default configurations for the user.

        Args:
            user_id: User ID who owns the configuration
            config: Configuration data to create

        Returns:
            Created UserConfiguration instance

        Raises:
            ValueError: If S3 config file does not exist
        """
        logging.info(
            f"[UserConfigurationService] Creating configuration '{config.name}' for user {user_id}"
        )

        async with self._session_factory() as session:
            # If this should be default, unset other defaults first
            if config.is_default:
                await self._unset_all_defaults(session, user_id)

            # Create new configuration
            new_config = UserConfiguration(
                user_id=user_id,
                name=config.name,
                feature_settings=config.feature_settings,
                is_default=config.is_default,
            )

            session.add(new_config)
            await session.commit()
            await session.refresh(new_config)

            logging.info(
                f"[UserConfigurationService] Created configuration {new_config.id}"
            )
            return new_config

    async def get_user_configurations(self, user_id: UUID) -> list[UserConfiguration]:
        """Get all configurations for a user.

        Returns configurations ordered by creation date (newest first).

        Args:
            user_id: User ID to get configurations for

        Returns:
            List of UserConfiguration instances
        """
        logging.debug(
            f"[UserConfigurationService] Fetching configurations for user {user_id}"
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(UserConfiguration)
                .where(UserConfiguration.user_id == user_id)
                .order_by(UserConfiguration.created_at.desc())
            )
            configurations = result.scalars().all()

            logging.info(
                f"[UserConfigurationService] Found {len(configurations)} configurations for user {user_id}"
            )
            return list(configurations)

    async def get_configuration(
        self, config_id: UUID, user_id: UUID
    ) -> Optional[UserConfiguration]:
        """Get a specific configuration by ID.

        Verifies that the configuration belongs to the specified user.

        Args:
            config_id: Configuration ID
            user_id: User ID for ownership verification

        Returns:
            UserConfiguration if found and owned by user, None otherwise
        """
        logging.debug(
            f"[UserConfigurationService] Fetching configuration {config_id} for user {user_id}"
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(UserConfiguration).where(
                    UserConfiguration.id == config_id,
                    UserConfiguration.user_id == user_id,
                )
            )
            config = result.scalar_one_or_none()

            if config:
                logging.info(
                    f"[UserConfigurationService] Found configuration {config_id}"
                )
            else:
                logging.debug(
                    f"[UserConfigurationService] Configuration {config_id} not found or access denied"
                )

            return config

    async def get_default_configuration(
        self, user_id: UUID
    ) -> Optional[UserConfiguration]:
        """Get the user's default configuration.

        Args:
            user_id: User ID

        Returns:
            Default UserConfiguration if exists, None otherwise
        """
        logging.debug(
            f"[UserConfigurationService] Fetching default configuration for user {user_id}"
        )

        async with self._session_factory() as session:
            result = await session.execute(
                select(UserConfiguration).where(
                    UserConfiguration.user_id == user_id,
                    UserConfiguration.is_default == True,  # noqa: E712
                )
            )
            config = result.scalar_one_or_none()

            if config:
                logging.info(
                    f"[UserConfigurationService] Found default configuration {config.id}"
                )
            else:
                logging.debug(
                    f"[UserConfigurationService] No default configuration for user {user_id}"
                )

            return config

    async def update_configuration(
        self,
        config_id: UUID,
        user_id: UUID,
        updates: UserConfigurationUpdate,
    ) -> UserConfiguration:
        """Update a configuration.

        Verifies ownership before updating. If is_default is set to True,
        unsets all other default configurations. Validates S3 path if changed.

        Args:
            config_id: Configuration ID to update
            user_id: User ID for ownership verification
            updates: Fields to update

        Returns:
            Updated UserConfiguration

        Raises:
            ValueError: If configuration not found, access denied, or S3 validation fails
        """
        logging.info(
            f"[UserConfigurationService] Updating configuration {config_id} for user {user_id}"
        )

        async with self._session_factory() as session:
            # Get configuration and verify ownership
            result = await session.execute(
                select(UserConfiguration).where(
                    UserConfiguration.id == config_id,
                    UserConfiguration.user_id == user_id,
                )
            )
            config = result.scalar_one_or_none()

            if not config:
                logging.error(
                    f"[UserConfigurationService] Configuration {config_id} not found or access denied"
                )
                raise ValueError("Configuration not found or access denied")

            # If setting as default, unset other defaults first
            if updates.is_default is True:
                await self._unset_all_defaults(session, user_id)

            # Update fields
            if updates.name is not None:
                config.name = updates.name
            if updates.feature_settings is not None:
                config.feature_settings = updates.feature_settings
            if updates.is_default is not None:
                config.is_default = updates.is_default

            await session.commit()
            await session.refresh(config)

            logging.info(
                f"[UserConfigurationService] Updated configuration {config_id}"
            )
            return config

    async def set_default_configuration(
        self, config_id: UUID, user_id: UUID
    ) -> UserConfiguration:
        """Set a configuration as the user's default.

        Unsets all other default configurations for the user before setting
        this one as default.

        Args:
            config_id: Configuration ID to set as default
            user_id: User ID for ownership verification

        Returns:
            Updated UserConfiguration

        Raises:
            ValueError: If configuration not found or access denied
        """
        logging.info(
            f"[UserConfigurationService] Setting configuration {config_id} as default for user {user_id}"
        )

        async with self._session_factory() as session:
            # Get configuration and verify ownership
            result = await session.execute(
                select(UserConfiguration).where(
                    UserConfiguration.id == config_id,
                    UserConfiguration.user_id == user_id,
                )
            )
            config = result.scalar_one_or_none()

            if not config:
                logging.error(
                    f"[UserConfigurationService] Configuration {config_id} not found or access denied"
                )
                raise ValueError("Configuration not found or access denied")

            # Unset all other defaults
            await self._unset_all_defaults(session, user_id)

            # Set this as default
            config.is_default = True
            await session.commit()
            await session.refresh(config)

            logging.info(
                f"[UserConfigurationService] Set configuration {config_id} as default"
            )
            return config

    async def delete_configuration(self, config_id: UUID, user_id: UUID) -> bool:
        """Delete a configuration.

        Verifies ownership before deleting.

        Args:
            config_id: Configuration ID to delete
            user_id: User ID for ownership verification

        Returns:
            True if deleted, False if not found or access denied
        """
        logging.info(
            f"[UserConfigurationService] Deleting configuration {config_id} for user {user_id}"
        )

        async with self._session_factory() as session:
            # Get configuration and verify ownership
            result = await session.execute(
                select(UserConfiguration).where(
                    UserConfiguration.id == config_id,
                    UserConfiguration.user_id == user_id,
                )
            )
            config = result.scalar_one_or_none()

            if not config:
                logging.debug(
                    f"[UserConfigurationService] Configuration {config_id} not found or access denied"
                )
                return False

            # Delete configuration
            await session.delete(config)
            await session.commit()

            logging.info(
                f"[UserConfigurationService] Deleted configuration {config_id}"
            )
            return True

    async def _unset_all_defaults(self, session: AsyncSession, user_id: UUID) -> None:
        """Unset all default configurations for a user.

        This is a helper method used internally when setting a new default
        configuration or creating one with is_default=True.

        Args:
            session: Active database session
            user_id: User ID
        """
        logging.debug(
            f"[UserConfigurationService] Unsetting all defaults for user {user_id}"
        )

        await session.execute(
            update(UserConfiguration)
            .where(
                UserConfiguration.user_id == user_id,
                UserConfiguration.is_default == True,  # noqa: E712
            )
            .values(is_default=False)
        )


# Singleton instance
_user_configuration_service: Optional[UserConfigurationService] = None


def get_user_configuration_service() -> UserConfigurationService:
    """Get global user configuration service instance (Singleton pattern).

    This function follows the project's service pattern for singleton instances.
    The service is initialized with database session factory and S3 service.

    Returns:
        Global user configuration service instance
    """
    global _user_configuration_service
    if _user_configuration_service is None:
        logging.info("[UserConfigurationService] Initializing singleton instance")

        from graal.database.base import get_async_session_maker
        from graal.utils.s3.s3_service import get_s3_service

        session_factory = get_async_session_maker()
        s3_service = get_s3_service()

        _user_configuration_service = UserConfigurationService(
            session_factory, s3_service
        )

    return _user_configuration_service
