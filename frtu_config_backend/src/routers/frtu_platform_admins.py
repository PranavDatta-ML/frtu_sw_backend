
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, Request, Depends

from src import Settings
from src.middleware.CreatePermissionMiddleware import  require_permission
# from src.routers.frtu_users import user_login
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate, FRTUPlatformAdminOut, FRTUPlatformAdminUpdate
from src.utils.entity_scope import user_can_access_entity
from src.views.frtu_platform_admins import  create_platform_admin, delete_platform_admin, get_platform_admin, get_platform_admin_hierarchy, list_platform_admins, update_platform_admin

router = APIRouter(
    prefix="/api/platform-admin",
    tags=['frtu_platform_admin']
)

# CREATE
@router.post("/", response_model=FRTUPlatformAdminOut)
async def api_create_platform_admin(data: FRTUPlatformAdminCreate,user_id: UUID = Depends(require_permission("edit", "PLATFORM_ADMIN"))):
    return await create_platform_admin(data, creator_id=user_id)

# READ ALL
@router.get("/", response_model=list[FRTUPlatformAdminOut])
async def api_list_platform_admins(
    user_id: UUID = Depends(require_permission("view", "PLATFORM_ADMIN"))
):
    return await list_platform_admins()

@router.get("/{platform_admin_id}")
async def get_platform_admin_by_id(platform_admin_id: UUID, user_id: UUID = Depends(require_permission("view", "PLATFORM_ADMIN"))):
    allowed = await user_can_access_entity(user_id, platform_admin_id)
    if not allowed:
        raise HTTPException(status_code=403,detail="You cannot access this Platform Admin")

    return await get_platform_admin(platform_admin_id)

# UPDATE
@router.put("/{platform_admin_id}")
async def api_update_platform_admin(
    platform_admin_id: UUID,
    data: FRTUPlatformAdminUpdate,
    user_id: UUID = Depends(require_permission("edit", "PLATFORM_ADMIN"))
):
    return await update_platform_admin(platform_admin_id, data)


# DELETE
@router.delete("/{platform_admin_id}")
async def api_delete_platform_admin(
    platform_admin_id: UUID,
    user_id: UUID = Depends(require_permission("edit", "PLATFORM_ADMIN"))
):
    return await delete_platform_admin(platform_admin_id)


# HIERARCHY (roles + permissions)
@router.get("/{platform_admin_id}/hierarchy")
async def api_platform_admin_hierarchy(platform_admin_id: UUID,user_id: UUID = Depends(require_permission("view", "PLATFORM_ADMIN"))):
    return await get_platform_admin_hierarchy(platform_admin_id)


