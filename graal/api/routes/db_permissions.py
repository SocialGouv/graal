"""
Database Permissions API

Provides endpoints for:
- Listing all permissions for a DB
- Assigning a role to a user (owner‑only)
- Removing a user's role (owner‑only)
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from graal.api.services.authorization_service import (
    AuthorizationService,
    DbRole,
    get_authorization_service,
)
from graal.api.services.database_permission_service import (
    get_database_permission_service,
)

AUTH_SERVICE_DEP = Depends(get_authorization_service)

router = APIRouter(prefix="/api/v1/databases")


@router.get("/{db_id}/permissions")
async def list_db_permissions(
    db_id: str,
    request: Request,
    auth: AuthorizationService = AUTH_SERVICE_DEP,
):
    """
    List all permission entries for a database.
    Only owners may view the full permission list.
    """
    await auth.require_db_role(db_id, DbRole.owner, request=request)

    perm_service = get_database_permission_service()
    perms = await perm_service.list_roles_for_db(db_id)
    return [
        {
            "db_id": str(p.db_id),
            "user_id": str(p.user_id),
            "role": p.role,
            "created_at": p.created_at,
        }
        for p in perms
    ]


@router.post("/{db_id}/permissions/{target_user_id}")
async def set_db_permission(
    db_id: str,
    target_user_id: str,
    role: str,
    request: Request,
    auth: AuthorizationService = AUTH_SERVICE_DEP,
):
    """
    Assign a role to a user for a DB.
    Only owners may assign roles.
    """
    if role not in (DbRole.owner, DbRole.writer, DbRole.reader):
        raise HTTPException(status_code=400, detail="Invalid role")

    await auth.require_db_role(db_id, DbRole.owner, request=request)

    perm_service = get_database_permission_service()
    try:
        await perm_service.set_user_role(db_id, target_user_id, role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"status": "ok", "message": "Role updated"}


@router.delete("/{db_id}/permissions/{target_user_id}")
async def delete_db_permission(
    db_id: str,
    target_user_id: str,
    request: Request,
    auth: AuthorizationService = AUTH_SERVICE_DEP,
):
    """
    Remove a user's role for a DB.
    Only owners may remove roles.
    """
    await auth.require_db_role(db_id, DbRole.owner, request=request)

    perm_service = get_database_permission_service()
    try:
        await perm_service.remove_user_role(db_id, target_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"status": "ok", "message": "Role removed"}
