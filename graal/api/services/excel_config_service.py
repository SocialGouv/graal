"""Excel config service for managing uploaded Excel configuration files."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from graal.api.models.requests import ExcelConfigPermissionRequest
from graal.database.enums import ExcelConfigRoleEnum
from graal.database.models import ExcelConfigManifest, ExcelConfigPermission, User
from graal.database.schemas import ExcelConfigManifestCreate
from graal.utils.s3.config_s3_service import ConfigS3Service
from graal.utils.s3.s3_service import S3Service

logging.config.fileConfig("logging.conf")


class ExcelConfigService:
    """Service layer for Excel config manifests and permissions."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        s3_service: S3Service,
    ) -> None:
        self._session_factory = session_factory
        self._s3_service = s3_service
        self._config_s3: ConfigS3Service = s3_service.config

    async def list_configs_for_user(self, user_id: UUID) -> list[ExcelConfigManifest]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExcelConfigManifest)
                .join(
                    ExcelConfigPermission,
                    ExcelConfigPermission.config_id == ExcelConfigManifest.id,
                )
                .where(ExcelConfigPermission.user_id == user_id)
                .order_by(ExcelConfigManifest.created_at.desc())
            )
            return list(result.scalars().all())

    async def list_all_configs(self) -> list[ExcelConfigManifest]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExcelConfigManifest).order_by(
                    ExcelConfigManifest.created_at.desc()
                )
            )
            return list(result.scalars().all())

    async def list_configs_with_roles(
        self, user_id: UUID
    ) -> list[tuple[ExcelConfigManifest, ExcelConfigPermission]]:
        async with self._session_factory() as session:
            query = (
                select(ExcelConfigManifest, ExcelConfigPermission)
                .join(
                    ExcelConfigPermission,
                    ExcelConfigPermission.config_id == ExcelConfigManifest.id,
                )
                .where(ExcelConfigPermission.user_id == user_id)
                .order_by(ExcelConfigManifest.created_at.desc())
            )
            result = await session.execute(query)
            return list(result.all())

    async def get_manifest(self, config_id: UUID) -> ExcelConfigManifest | None:
        async with self._session_factory() as session:
            return await session.get(ExcelConfigManifest, config_id)

    async def get_user_permission(
        self, config_id: UUID, user_id: UUID
    ) -> ExcelConfigPermission | None:
        async with self._session_factory() as session:
            return await session.get(
                ExcelConfigPermission,
                {"config_id": config_id, "user_id": user_id},
            )

    async def get_user_role(
        self, config_id: UUID, user_id: UUID
    ) -> ExcelConfigRoleEnum | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExcelConfigPermission.role).where(
                    ExcelConfigPermission.config_id == config_id,
                    ExcelConfigPermission.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()

    async def _count_owners(self, session: AsyncSession, config_id: UUID) -> int:
        result = await session.execute(
            select(ExcelConfigPermission).where(
                ExcelConfigPermission.config_id == config_id,
                ExcelConfigPermission.role == ExcelConfigRoleEnum.owner,
            )
        )
        return len(result.scalars().all())

    async def create_config(
        self,
        config_id: UUID,
        owner_id: UUID,
        manifest_data: ExcelConfigManifestCreate,
        file_bytes: bytes,
    ) -> ExcelConfigManifest:
        extension = Path(manifest_data.file_name).suffix
        stored_filename = f"{uuid4()}{extension}"
        s3_key = self._config_s3.build_config_key(stored_filename)
        await self._config_s3.upload_config_file_by_key(s3_key, file_bytes)

        async with self._session_factory() as session:
            new_manifest = ExcelConfigManifest(
                id=config_id,
                owner_user_id=owner_id,
                file_name=manifest_data.file_name,
                s3_key=s3_key,
                file_size_bytes=manifest_data.file_size_bytes,
                sheet_metadata=manifest_data.sheet_metadata,
            )
            session.add(new_manifest)
            await session.flush()

            permission = ExcelConfigPermission(
                config_id=new_manifest.id,
                user_id=owner_id,
                role=ExcelConfigRoleEnum.owner,
            )
            session.add(permission)

            await session.commit()
            await session.refresh(new_manifest)

            return new_manifest

    async def delete_config(self, config_id: UUID, requester_id: UUID) -> None:
        async with self._session_factory() as session:
            manifest = await session.get(ExcelConfigManifest, config_id)
            if not manifest:
                raise ValueError("Configuration not found")
            # Verify ownership
            perm = await session.get(
                ExcelConfigPermission,
                {"config_id": config_id, "user_id": requester_id},
            )
            if not perm or perm.role != ExcelConfigRoleEnum.owner:
                raise ValueError("Only owners can delete configs")
            # Delete S3 object first using the stored key
            await self._config_s3.delete_config_file_by_key(manifest.s3_key)
            await session.execute(
                delete(ExcelConfigPermission).where(
                    ExcelConfigPermission.config_id == config_id
                )
            )
            await session.delete(manifest)
            await session.commit()

    async def delete_config_as_admin(self, config_id: UUID) -> None:
        async with self._session_factory() as session:
            manifest = await session.get(ExcelConfigManifest, config_id)
            if not manifest:
                raise ValueError("Configuration not found")
            await self._config_s3.delete_config_file_by_key(manifest.s3_key)
            await session.execute(
                delete(ExcelConfigPermission).where(
                    ExcelConfigPermission.config_id == config_id
                )
            )
            await session.delete(manifest)
            await session.commit()

    async def assign_permission(
        self, config_id: UUID, request: ExcelConfigPermissionRequest
    ) -> ExcelConfigPermission:
        async with self._session_factory() as session:
            existing = await session.get(
                ExcelConfigPermission,
                {"config_id": config_id, "user_id": request.user_id},
            )

            if existing:
                if (
                    existing.role == ExcelConfigRoleEnum.owner
                    and ExcelConfigRoleEnum(request.role) != ExcelConfigRoleEnum.owner
                    and await self._count_owners(session, config_id) <= 1
                ):
                    raise ValueError("Cannot demote the last owner")
                existing.role = ExcelConfigRoleEnum(request.role)
                await session.commit()
                await session.refresh(existing)
                return existing

            permission = ExcelConfigPermission(
                config_id=config_id,
                user_id=request.user_id,
                role=ExcelConfigRoleEnum(request.role),
            )
            session.add(permission)
            await session.commit()
            await session.refresh(permission)
            return permission

    async def remove_permission(self, config_id: UUID, user_id: UUID) -> None:
        async with self._session_factory() as session:
            perm = await session.get(
                ExcelConfigPermission,
                {"config_id": config_id, "user_id": user_id},
            )
            if perm is None:
                raise ValueError("Permission not found")

            if perm.role == ExcelConfigRoleEnum.owner:
                if await self._count_owners(session, config_id) <= 1:
                    raise ValueError("Cannot remove last owner")

            await session.delete(perm)
            await session.commit()

    async def get_permissions(self, config_id: UUID) -> list[ExcelConfigPermission]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExcelConfigPermission).where(
                    ExcelConfigPermission.config_id == config_id
                )
            )
            return list(result.scalars().all())

    async def get_permissions_with_users(
        self, config_id: UUID
    ) -> list[tuple[ExcelConfigPermission, User | None]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExcelConfigPermission, User)
                .join(User, User.id == ExcelConfigPermission.user_id, isouter=True)
                .where(ExcelConfigPermission.config_id == config_id)
            )
            return list(result.all())

    async def download_config_file(self, manifest: ExcelConfigManifest) -> bytes:
        return await self._config_s3.download_config_file_by_key(manifest.s3_key)


# Singleton
_excel_config_service: ExcelConfigService | None = None


def get_excel_config_service() -> ExcelConfigService:
    global _excel_config_service
    if _excel_config_service is None:
        from graal.database.base import get_async_session_maker
        from graal.utils.s3.s3_service import get_s3_service

        _excel_config_service = ExcelConfigService(
            get_async_session_maker(), get_s3_service()
        )
    return _excel_config_service
