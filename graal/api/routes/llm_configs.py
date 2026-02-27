"""API routes for managing LLM configs.

These endpoints power:
- the Processing UI (list configs to select one)
- the Admin UI (CRUD)
"""

from __future__ import annotations

import logging
import logging.config
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from graal.api.dependencies.auth import (
    AdminUser,
    CurrentUser,
    get_current_user,
    require_admin,
)
from graal.api.services.llm_config_service import get_llm_config_service
from graal.database.schemas import LlmConfigCreate, LlmConfigRead, LlmConfigUpdate

logging.config.fileConfig("logging.conf")


router = APIRouter(
    tags=["LLM Configs"],
    dependencies=[Depends(get_current_user)],
)


admin_router = APIRouter(
    prefix="/admin/llm-configs",
    tags=["LLM Configs"],
    dependencies=[Depends(require_admin)],
)


@router.get("/llm-configs", response_model=list[LlmConfigRead])
async def list_llm_configs(_current_user: CurrentUser):
    """List LLM configs for authenticated users."""

    service = get_llm_config_service()
    configs = await service.list_configs()
    return [LlmConfigRead.model_validate(c) for c in configs]


@admin_router.get("", response_model=list[LlmConfigRead])
async def list_llm_configs_admin(_admin_user: AdminUser):
    """List all LLM configs (admin only)."""

    service = get_llm_config_service()
    configs = await service.list_configs()
    return [LlmConfigRead.model_validate(c) for c in configs]


@admin_router.post(
    "",
    response_model=LlmConfigRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_config(config: LlmConfigCreate, _admin_user: AdminUser):
    """Create a new LLM config (admin only)."""

    service = get_llm_config_service()
    try:
        created = await service.create_config(config)
        return LlmConfigRead.model_validate(created)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.patch("/{config_id}", response_model=LlmConfigRead)
async def update_llm_config(
    config_id: UUID,
    updates: LlmConfigUpdate,
    _admin_user: AdminUser,
):
    """Update an LLM config (admin only)."""

    service = get_llm_config_service()
    try:
        updated = await service.update_config(config_id, updates)
        return LlmConfigRead.model_validate(updated)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail="LLM config not found") from exc
        raise HTTPException(status_code=400, detail=msg) from exc


@admin_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(config_id: UUID, _admin_user: AdminUser):
    """Delete an LLM config (admin only)."""

    service = get_llm_config_service()
    try:
        await service.delete_config(config_id)
        return None
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="LLM config not found") from exc
