from uuid import UUID
from fastapi import APIRouter, Depends

from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.schemas.rbac import PermissionCreate, RoleCreate, UserRoleAssign
from src.utils.jwt_tokens import decode_access_token
from src.validators.rbac import current_user, require_permission
from src.views.rbac import get_my_rbac_info, get_roles_visible_to_me, get_users_created_by_me

router = APIRouter(prefix="/rbac", tags=["RBAC"])

def get_current_user(token: str):
    return UUID(decode_access_token(token)["sub"])

@router.post("/roles/")
async def create_role(
    data: RoleCreate,
    user_id: UUID = Depends(require_permission("edit", "ROLES"))
):
    role = await FRTURoles.insert(
        user_id=user_id,
        name=data.name,
        description=data.description,
        attribute=data.attribute,
    )
    return {"status": "created", "role_id": str(role.id)}


@router.post("/permissions/")
async def create_permission(
    data: PermissionCreate,
    user_id: UUID = Depends(require_permission("edit", "PERMISSION"))
):
    perm = await FRTUPermissions.insert(
        user_id=user_id,
        attribute=data.attribute,
    )
    return {"permission_id": str(perm.id)}

@router.post("/role-permissions/")
async def assign_permission(
    data: PermissionCreate,
    user_id: UUID = Depends(require_permission("edit", "PERMISSION"))
):
    await FRTURolePermissions.insert(
        role_id=data.role_id,
        permission_id=data.permission_id
    )
    return {"status": "assigned"}


@router.post("/user-roles/")
async def assign_role(
    data: UserRoleAssign,
    user_id: UUID = Depends(require_permission("edit", "USER"))
):
    await FRTUUserAssignment.insert(
        user_id=data.user_id,
        role_id=data.role_id,
        admin_id=user_id
    )
    return {"status": "assigned"}

@router.get("/rbac/me")
async def get_my_rbac(
    user_id: UUID = Depends(current_user)
):
    return await get_my_rbac_info(user_id)

@router.get("/rbac/my-users")
async def get_my_users(
    user_id: UUID = Depends(current_user)
):
    return await get_users_created_by_me(user_id)

@router.get("/rbac/my-roles")
async def get_my_roles(
    user_id: UUID = Depends(current_user)
):
    return await get_roles_visible_to_me(user_id)
