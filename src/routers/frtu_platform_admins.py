
from uuid import UUID
from fastapi import APIRouter, Header, Request, Depends

from src import Settings
from src.middleware.CreatePermissionMiddleware import require_create_permission
# from src.routers.frtu_users import user_login
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate, FRTUPlatformAdminOut
from src.views.frtu_platform_admins import  create_platform_admin

router = APIRouter(
    prefix="/api/platform-admin",
    tags=['frtu_platform_admin']
)

@router.post("/", response_model=FRTUPlatformAdminOut)
async def api_create_platform_admin(
    data: FRTUPlatformAdminCreate,
    user_id: UUID = Depends(require_create_permission)
):
    platform_admin = await create_platform_admin(data, creator_id=user_id)
    return platform_admin


# @router.post("/", response_model=FRTUPlatformAdminOut)
# async def api_create_platform_admin(
#     data: FRTUPlatformAdminCreate,
#     user_id: UUID = Depends(
#         require_create_permission(
#             resource="PLATFORM_ADMIN",      # Permission check
#             allowed_roles=["ADMIN"]         # Role restriction
#         )
#     )
# ):
#     return await create_platform_admin(data, creator_id=user_id)




