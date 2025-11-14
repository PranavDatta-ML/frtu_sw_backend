from fastapi import APIRouter, Depends, Path, Query
from typing import List
from uuid import UUID

from src.schemas.frtu_roles import FRTURoleCreate, FRTURoleUpdate, FRTURoleRead
from src.middleware.CreatePermissionMiddleware import require_create_permission
from src.middleware.ReadPermissionMiddleware import require_read_permission
from src.views.frtu_roles import create_role, delete_role, get_role, list_roles, update_role


router = APIRouter(prefix="/roles", tags=["roles"])

@router.post("/", response_model=FRTURoleRead)
async def api_create_role(
    role_create: FRTURoleCreate,
    user_id: UUID = Depends(require_create_permission)
):
    return await create_role(role_create, user_id)

@router.get("/", response_model=List[FRTURoleRead])
async def api_list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    user_id: UUID = Depends(require_read_permission)
):
    return await list_roles(skip, limit)

@router.get("/{role_id}", response_model=FRTURoleRead)
async def api_get_role(
    role_id: UUID = Path(...),
    user_id: UUID = Depends(require_read_permission)
):
    return await get_role(role_id)

@router.put("/{role_id}", response_model=FRTURoleRead)
async def api_update_role(role_id: UUID,
    role_update: FRTURoleUpdate,
    user_id: UUID = Depends(require_create_permission)
):
    return await update_role(role_id, role_update)

@router.delete("/{role_id}")
async def api_delete_role(
    role_id: UUID,
    user_id: UUID = Depends(require_create_permission)
):
    await delete_role(role_id)
    return {"message": "Role deleted successfully"}


