from fastapi import APIRouter, Depends
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission, require_permission
from src.schemas.frtu_role_permissions import AssignRolePermission, FRTURolePermissionRead, UpdateRolePermission
from src.views.frtu_role_permissions import assign_permission_to_role, delete_role_permission, get_role_permission, list_role_permissions, update_role_permission


router = APIRouter(
    prefix="/api/role-permissions",
    tags=["frtu_role_permissions"]
)


@router.post("/", response_model=FRTURolePermissionRead)
async def api_assign_permission_to_role(data: AssignRolePermission,user_id: UUID = Depends(require_permission("edit", "ROLE_PERMISSION"))):
    return await assign_permission_to_role(data, user_id)


# READ ALL permissions assigned to a role
@router.get("/{role_id}", response_model=list[FRTURolePermissionRead])
async def api_list_permissions_of_role(role_id: UUID,user_id: UUID = Depends(require_permission("view", "ROLE_PERMISSION"))):
    return await list_role_permissions(role_id)


# READ a specific mapping
@router.get("/{role_id}/{permission_id}", response_model=FRTURolePermissionRead)
async def api_get_single_mapping(role_id: UUID,permission_id: UUID,user_id: UUID = Depends(require_permission("view", "ROLE_PERMISSION"))):
    return await get_role_permission(role_id, permission_id)


# UPDATE mapping
@router.put("/{role_id}/{permission_id}", response_model=FRTURolePermissionRead)
async def api_update_role_permission(role_id: UUID,permission_id: UUID,payload: UpdateRolePermission,user_id: UUID = Depends(require_permission("edit", "ROLE_PERMISSION"))):
    return await update_role_permission(role_id,permission_id,payload.new_permission_id,user_id,)


# DELETE mapping
@router.delete("/{role_id}/{permission_id}")
async def api_delete_role_permission(role_id: UUID,permission_id: UUID,user_id: UUID = Depends(require_permission("edit", "ROLE_PERMISSION"))):
    return await delete_role_permission(role_id, permission_id)