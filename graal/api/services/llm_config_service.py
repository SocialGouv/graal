"""LLM config service for managing LLM configurations.

This service stores admin-managed LLM connection profiles (provider + model + credentials).
They are later used by the web processing service to create LLM API clients.
"""

from __future__ import annotations

import logging
import logging.config
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.database.models import LlmConfig
from graal.database.schemas import LlmConfigCreate, LlmConfigUpdate

logging.config.fileConfig("logging.conf")


class LlmConfigService:
    """Service layer for LLM config CRUD operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_configs(self) -> list[LlmConfig]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(LlmConfig).order_by(LlmConfig.updated_at.desc())
            )
            return list(result.scalars().all())

    async def get_config(self, config_id: UUID) -> LlmConfig | None:
        async with self._session_factory() as session:
            return await session.get(LlmConfig, config_id)

    async def create_config(self, data: LlmConfigCreate) -> LlmConfig:
        async with self._session_factory() as session:
            new_config = LlmConfig(
                name=data.name,
                provider=data.provider,
                model_name=data.model_name,
                base_url=data.base_url,
                api_key=data.api_key,
                rate_limit_per_minute=data.rate_limit_per_minute,
            )
            session.add(new_config)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise ValueError("LLM config name already exists") from exc

            await session.refresh(new_config)
            return new_config

    async def update_config(
        self, config_id: UUID, updates: LlmConfigUpdate
    ) -> LlmConfig:
        async with self._session_factory() as session:
            config = await session.get(LlmConfig, config_id)
            if config is None:
                raise ValueError("LLM config not found")

            # Partial update
            update_data = updates.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key == "rate_limit_per_minute" and value is None:
                    raise ValueError("rate_limit_per_minute cannot be null")
                setattr(config, key, value)

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise ValueError("LLM config name already exists") from exc

            await session.refresh(config)
            return config

    async def delete_config(self, config_id: UUID) -> None:
        async with self._session_factory() as session:
            config = await session.get(LlmConfig, config_id)
            if config is None:
                raise ValueError("LLM config not found")
            await session.delete(config)
            await session.commit()


_llm_config_service: Optional[LlmConfigService] = None


def get_llm_config_service() -> LlmConfigService:
    global _llm_config_service
    if _llm_config_service is None:
        from graal.database.base import get_async_session_maker

        _llm_config_service = LlmConfigService(get_async_session_maker())
    return _llm_config_service
