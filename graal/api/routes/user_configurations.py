"""
User Configuration API routes.

This module provides endpoints for users to manage their saved configuration presets,
allowing them to create, read, update, and delete configurations, as well as set defaults.
"""

import logging
import logging.config
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException, Request, status

from graal.api.services.authorization_service import get_authorization_service
from graal.api.services.user_configuration_service import (
    get_user_configuration_service,
)
from graal.database.schemas import (
    UserConfigurationCreate,
    UserConfigurationRead,
    UserConfigurationUpdate,
)

logging.config.fileConfig("logging.conf")


router = APIRouter(prefix="/users/me/configurations", tags=["User Configurations"])


@router.get("", response_model=list[UserConfigurationRead])
async def list_user_configurations(
    request: Request, session: Optional[str] = Cookie(default=None)
):
    """
    List all configurations for the current user.

    Returns configurations ordered by creation date (newest first).

    Args:
        request: FastAPI request object
        session: Session cookie value

    Returns:
        List of UserConfigurationRead schemas

    Raises:
        HTTPException: 401 if not authenticated
    """
    logging.info("[API] Listing user configurations")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Get configurations
        config_service = get_user_configuration_service()
        configurations = await config_service.get_user_configurations(user_id)

        logging.info(
            f"[API] Retrieved {len(configurations)} configurations for user {user_id}"
        )
        return [
            UserConfigurationRead.model_validate(config) for config in configurations
        ]

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to list configurations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list configurations"
        ) from e


@router.post(
    "", response_model=UserConfigurationRead, status_code=status.HTTP_201_CREATED
)
async def create_user_configuration(
    config: UserConfigurationCreate,
    request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """
    Create a new configuration for the current user.

    Validates that the S3 config file exists before creating.
    If is_default is True, unsets all other default configurations.

    Args:
        config: Configuration data to create
        request: FastAPI request object
        session: Session cookie value

    Returns:
        Created UserConfigurationRead schema

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 400 if S3 file validation fails
    """
    logging.info(f"[API] Creating configuration '{config.name}'")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Create configuration
        config_service = get_user_configuration_service()
        new_config = await config_service.create_configuration(user_id, config)

        logging.info(f"[API] Created configuration {new_config.id}")
        return UserConfigurationRead.model_validate(new_config)

    except ValueError as e:
        logging.warning(f"[API] Validation error creating configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to create configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create configuration"
        ) from e


@router.get("/default", response_model=UserConfigurationRead)
async def get_default_configuration(
    request: Request, session: Optional[str] = Cookie(default=None)
):
    """
    Get the user's default configuration.

    Args:
        request: FastAPI request object
        session: Session cookie value

    Returns:
        UserConfigurationRead schema of default configuration

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if no default configuration set
    """
    logging.info("[API] Getting default configuration")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Get default configuration
        config_service = get_user_configuration_service()
        config = await config_service.get_default_configuration(user_id)

        if not config:
            logging.warning(f"[API] No default configuration for user {user_id}")
            raise HTTPException(status_code=404, detail="No default configuration set")

        logging.info(f"[API] Retrieved default configuration {config.id}")
        return UserConfigurationRead.model_validate(config)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to get default configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get default configuration"
        ) from e


@router.get("/{config_id}", response_model=UserConfigurationRead)
async def get_user_configuration(
    config_id: UUID,
    request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """
    Get a specific configuration by ID.

    Verifies that the configuration belongs to the current user.

    Args:
        config_id: Configuration UUID
        request: FastAPI request object
        session: Session cookie value

    Returns:
        UserConfigurationRead schema

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if not found or doesn't belong to user
    """
    logging.info(f"[API] Getting configuration {config_id}")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Get configuration
        config_service = get_user_configuration_service()
        config = await config_service.get_configuration(config_id, user_id)

        if not config:
            logging.warning(
                f"[API] Configuration {config_id} not found or access denied"
            )
            raise HTTPException(
                status_code=404, detail="Configuration not found or access denied"
            )

        logging.info(f"[API] Retrieved configuration {config_id}")
        return UserConfigurationRead.model_validate(config)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to get configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get configuration"
        ) from e


@router.patch("/{config_id}", response_model=UserConfigurationRead)
async def update_user_configuration(
    config_id: UUID,
    updates: UserConfigurationUpdate,
    request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """
    Update a configuration.

    Verifies ownership before updating. If is_default is set to True,
    unsets all other default configurations. Validates S3 path if changed.

    Args:
        config_id: Configuration UUID to update
        updates: Fields to update
        request: FastAPI request object
        session: Session cookie value

    Returns:
        Updated UserConfigurationRead schema

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if not found or doesn't belong to user
        HTTPException: 400 if S3 validation fails
    """
    logging.info(f"[API] Updating configuration {config_id}")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Update configuration
        config_service = get_user_configuration_service()
        updated_config = await config_service.update_configuration(
            config_id, user_id, updates
        )

        logging.info(f"[API] Updated configuration {config_id}")
        return UserConfigurationRead.model_validate(updated_config)

    except ValueError as e:
        logging.warning(f"[API] Validation error updating configuration: {e}")
        if "not found or access denied" in str(e):
            raise HTTPException(
                status_code=404, detail="Configuration not found or access denied"
            ) from e
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to update configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update configuration"
        ) from e


@router.post("/{config_id}/set-default", response_model=UserConfigurationRead)
async def set_default_configuration(
    config_id: UUID,
    request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """
    Set a configuration as the user's default.

    Unsets all other default configurations before setting this one as default.

    Args:
        config_id: Configuration UUID to set as default
        request: FastAPI request object
        session: Session cookie value

    Returns:
        Updated UserConfigurationRead schema

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if not found or doesn't belong to user
    """
    logging.info(f"[API] Setting configuration {config_id} as default")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Set as default
        config_service = get_user_configuration_service()
        updated_config = await config_service.set_default_configuration(
            config_id, user_id
        )

        logging.info(f"[API] Set configuration {config_id} as default")
        return UserConfigurationRead.model_validate(updated_config)

    except ValueError as e:
        logging.warning(f"[API] Error setting default configuration: {e}")
        raise HTTPException(
            status_code=404, detail="Configuration not found or access denied"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to set default configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to set default configuration"
        ) from e


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_configuration(
    config_id: UUID,
    request: Request,
    session: Optional[str] = Cookie(default=None),
):
    """
    Delete a configuration.

    Verifies ownership before deleting.

    Args:
        config_id: Configuration UUID to delete
        request: FastAPI request object
        session: Session cookie value

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if not found or doesn't belong to user
    """
    logging.info(f"[API] Deleting configuration {config_id}")

    try:
        # Get current user
        auth_service = get_authorization_service()
        current_user = await auth_service.get_current_user(request, session)
        user_id = UUID(current_user.user_id)

        # Delete configuration
        config_service = get_user_configuration_service()
        deleted = await config_service.delete_configuration(config_id, user_id)

        if not deleted:
            logging.warning(
                f"[API] Configuration {config_id} not found or access denied"
            )
            raise HTTPException(
                status_code=404, detail="Configuration not found or access denied"
            )

        logging.info(f"[API] Deleted configuration {config_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[API] Failed to delete configuration: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete configuration"
        ) from e
