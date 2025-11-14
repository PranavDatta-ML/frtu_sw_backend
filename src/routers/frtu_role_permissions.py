# src/routers/frtu_role_permissions.py
from fastapi import APIRouter, Depends
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission
from src.schemas.frtu_role_permissions import AssignRolePermission, FRTURolePermissionRead
from src.views.frtu_role_permissions import assign_permission_to_role


router = APIRouter(
    prefix="/api/role-permissions",
    tags=["frtu_role_permissions"]
)


@router.post("/", response_model=FRTURolePermissionRead)
async def api_assign_permission_to_role(
    data: AssignRolePermission,
    user_id: UUID = Depends(require_create_permission)
):
    return await assign_permission_to_role(data, assigned_by=user_id)
