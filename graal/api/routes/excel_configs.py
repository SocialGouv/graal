"""API routes for managing user-owned Excel configuration files."""

from __future__ import annotations

import logging
import logging.config
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from graal.api.dependencies.auth import (
    AdminUser,
    CurrentUser,
    get_current_user,
    require_admin,
)
from graal.api.models.requests import (
    ExcelConfigPermissionDeleteRequest,
    ExcelConfigPermissionRequest,
)
from graal.api.models.responses import (
    ExcelConfigListResponse,
    ExcelConfigManifestResponse,
    ExcelConfigPermissionResponse,
)
from graal.api.models.types import ExcelConfigId
from graal.api.services.authorization_service import get_authorization_service
from graal.api.services.excel_config_service import get_excel_config_service
from graal.database.enums import ExcelConfigRoleEnum
from graal.database.schemas import ExcelConfigManifestCreate

logging.config.fileConfig("logging.conf")
router = APIRouter(
    prefix="/configs",
    tags=["Excel Configs"],
    dependencies=[Depends(get_current_user)],
)


admin_router = APIRouter(
    prefix="/admin/excel-configs",
    tags=["Excel Configs"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=ExcelConfigListResponse)
async def list_configs(current_user: CurrentUser):
    service = get_excel_config_service()
    rows = await service.list_configs_with_roles(UUID(current_user.user_id))
    configs = [
        ExcelConfigManifestResponse(
            id=str(manifest.id),
            owner_user_id=str(manifest.owner_user_id),
            file_name=manifest.file_name,
            s3_key=manifest.s3_key,
            file_size_bytes=manifest.file_size_bytes,
            sheet_metadata=manifest.sheet_metadata,
            created_at=manifest.created_at,
            updated_at=manifest.updated_at,
            deleted_at=manifest.deleted_at,
            current_user_role=permission.role,
        )
        for manifest, permission in rows
    ]
    return ExcelConfigListResponse(configs=configs, total=len(configs))


@router.get("/{config_id}", response_model=ExcelConfigManifestResponse)
async def get_config(config_id: ExcelConfigId, current_user: CurrentUser):
    service = get_excel_config_service()
    manifest = await service.get_manifest(config_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Configuration not found")
    perm = await service.get_user_permission(config_id, UUID(current_user.user_id))
    if not perm:
        raise HTTPException(status_code=403, detail="Access denied")
    return ExcelConfigManifestResponse(
        id=str(manifest.id),
        owner_user_id=str(manifest.owner_user_id),
        file_name=manifest.file_name,
        s3_key=manifest.s3_key,
        file_size_bytes=manifest.file_size_bytes,
        sheet_metadata=manifest.sheet_metadata,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        deleted_at=manifest.deleted_at,
        current_user_role=perm.role,
    )


@router.post(
    "",
    response_model=ExcelConfigManifestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_config(
    current_user: CurrentUser,
    file: UploadFile,
):
    service = get_excel_config_service()

    if file.content_type not in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx files are supported",
        )

    file_bytes = await file.read()
    config_id = uuid4()
    s3_key = file.filename or f"{config_id}.xlsx"
    manifest = await service.create_config(
        config_id=config_id,
        owner_id=UUID(current_user.user_id),
        manifest_data=ExcelConfigManifestCreate(
            file_name=file.filename or "",
            s3_key=s3_key,
            file_size_bytes=len(file_bytes),
            sheet_metadata=None,
            owner_user_id=UUID(current_user.user_id),
        ),
        file_bytes=file_bytes,
    )

    return ExcelConfigManifestResponse(
        id=str(manifest.id),
        owner_user_id=str(manifest.owner_user_id),
        file_name=manifest.file_name,
        s3_key=manifest.s3_key,
        file_size_bytes=manifest.file_size_bytes,
        sheet_metadata=manifest.sheet_metadata,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        deleted_at=manifest.deleted_at,
        current_user_role=ExcelConfigRoleEnum.owner,
    )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    config_id: ExcelConfigId,
    request: Request,
    current_user: CurrentUser,
):
    service = get_excel_config_service()
    auth = get_authorization_service()
    await auth.require_config_role(
        config_id,
        ExcelConfigRoleEnum.owner,
        request,
    )
    try:
        await service.delete_config(config_id, UUID(current_user.user_id))
    except ValueError as exc:
        detail = str(exc)
        if detail == "Configuration not found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail == "Only owners can delete configs":
            status_code = status.HTTP_403_FORBIDDEN
        else:
            # Unexpected ValueError – surface as 500 or re-raise
            raise
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get(
    "/{config_id}/permissions",
    response_model=list[ExcelConfigPermissionResponse],
)
async def list_permissions(
    config_id: ExcelConfigId,
    request: Request,
    current_user: CurrentUser,
):
    service = get_excel_config_service()
    auth = get_authorization_service()
    await auth.require_config_role(
        config_id,
        ExcelConfigRoleEnum.owner,
        request,
    )
    permissions = await service.get_permissions_with_users(config_id)
    return [
        ExcelConfigPermissionResponse(
            config_id=str(permission.config_id),
            user_id=str(permission.user_id),
            email=user.email if user else None,
            role=permission.role,
            created_at=permission.created_at,
        )
        for permission, user in permissions
    ]


@router.post(
    "/{config_id}/permissions",
    response_model=ExcelConfigPermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_permission(
    config_id: ExcelConfigId,
    request: ExcelConfigPermissionRequest,
    http_request: Request,
):
    service = get_excel_config_service()
    auth = get_authorization_service()
    await auth.require_config_role(
        config_id,
        ExcelConfigRoleEnum.owner,
        http_request,
    )
    try:
        permission = await service.assign_permission(
            config_id,
            request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    permissions_with_users = await service.get_permissions_with_users(config_id)
    email = next(
        (
            user.email
            for permission_row, user in permissions_with_users
            if permission_row.user_id == permission.user_id and user is not None
        ),
        None,
    )
    return ExcelConfigPermissionResponse(
        config_id=str(permission.config_id),
        user_id=str(permission.user_id),
        email=email,
        role=permission.role,
        created_at=permission.created_at,
    )


@router.delete(
    "/{config_id}/permissions",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_permission(
    config_id: ExcelConfigId,
    request: ExcelConfigPermissionDeleteRequest,
    http_request: Request,
):
    service = get_excel_config_service()
    auth = get_authorization_service()
    await auth.require_config_role(
        config_id,
        ExcelConfigRoleEnum.owner,
        http_request,
    )
    try:
        await service.remove_permission(config_id, request.user_id)
    except ValueError as exc:
        detail = str(exc)
        if detail == "Permission not found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail == "Cannot remove last owner":
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            # Unexpected ValueError – let it propagate for now
            raise
        raise HTTPException(status_code=status_code, detail=detail) from exc


@admin_router.get("", response_model=ExcelConfigListResponse)
async def list_all_configs(admin_user: AdminUser):
    service = get_excel_config_service()
    manifests = await service.list_all_configs()
    configs = [
        ExcelConfigManifestResponse(
            id=str(manifest.id),
            owner_user_id=str(manifest.owner_user_id),
            file_name=manifest.file_name,
            s3_key=manifest.s3_key,
            file_size_bytes=manifest.file_size_bytes,
            sheet_metadata=manifest.sheet_metadata,
            created_at=manifest.created_at,
            updated_at=manifest.updated_at,
            deleted_at=manifest.deleted_at,
            current_user_role=ExcelConfigRoleEnum.owner,
        )
        for manifest in manifests
    ]
    return ExcelConfigListResponse(configs=configs, total=len(configs))


@admin_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config_as_admin(
    config_id: ExcelConfigId,
    admin_user: AdminUser,
):
    service = get_excel_config_service()
    try:
        await service.delete_config_as_admin(UUID(config_id))
    except ValueError as exc:
        detail = str(exc)
        if detail == "Configuration not found":
            status_code = status.HTTP_404_NOT_FOUND
        else:
            raise
        raise HTTPException(status_code=status_code, detail=detail) from exc
