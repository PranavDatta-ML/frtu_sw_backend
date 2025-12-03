from fastapi import APIRouter, Depends, Path, Query
from typing import List
from uuid import UUID

from src.schemas.frtu_permissions import FRTUPermissionCreate, FRTUPermissionUpdate, FRTUPermissionRead
from src.middleware.CreatePermissionMiddleware import require_create_permission, require_permission
from src.middleware.ReadPermissionMiddleware import require_read_permission
from src.views.frtu_permissions import create_permission, delete_permission, get_permission, list_permissions, read_permission_catalog, update_permission


# router = APIRouter(prefix="/permissions", tags=["permissions"])
router = APIRouter(prefix="/api", tags=["permissions"])

@router.post("/", response_model=FRTUPermissionRead)
async def api_create_permission(
    permission_create: FRTUPermissionCreate,
    # user_id: UUID = Depends(require_create_permission)
    user_id: UUID = Depends(require_permission("edit", "PERMISSION"))
):
    return await create_permission(permission_create, user_id)

@router.get("/permissions")
async def api_read_permission_catalog(
    # caller_id: UUID = Depends(require_permission("view", "PERMISSION")),
):
    return await read_permission_catalog()

@router.get("/", response_model=List[FRTUPermissionRead])
async def api_list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    user_id: UUID = Depends(require_permission("view", "PERMISSION"))
):
    return await list_permissions(skip, limit)

@router.get("/{permission_id}", response_model=FRTUPermissionRead)
async def api_get_permission(
    permission_id: UUID = Path(...),
    user_id: UUID = Depends(require_permission("view", "PERMISSION"))
):
    return await get_permission(permission_id)

@router.put("/{permission_id}", response_model=FRTUPermissionRead)
async def api_update_permission(
    permission_id: UUID,
    permission_update: FRTUPermissionUpdate,
    user_id: UUID = Depends(require_permission("edit", "PERMISSION"))
):
    return await update_permission(permission_id, permission_update)

@router.delete("/{permission_id}")
async def api_delete_permission(
    permission_id: UUID,
    user_id: UUID = Depends(require_permission("edit", "PERMISSION"))
):
    await delete_permission(permission_id)
    return {"message": "Permission deleted successfully"}



