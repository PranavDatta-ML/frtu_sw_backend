from uuid import UUID
from fastapi import APIRouter, Header, Query, Request, Depends
from fastapi.responses import JSONResponse
from src import Settings
from src.enums.FrtuDeviceType import FrtuDeviceType
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_auto_discover_module import AutoDiscoverRequest
from src.views.frtu_auto_discover_module import auto_discover_modules, auto_discover_modules_list, auto_discover_modules_msg

router = APIRouter(
    prefix="",
    tags=['frtu_auto_discover_modules_list']
)

@router.post("/auto_discover_modules")
async def api_auto_discover_modules(
    payload: AutoDiscoverRequest,
    user_id: UUID = Depends(require_permission("edit", "DEVICES")),
):
    return await auto_discover_modules(payload, user_id=user_id)


# @router.post("/auto_discover_modules/by_site")
# async def api_auto_discover_modules_by_site(
#     payload: AutoDiscoverBySitePayload,
#     user_id: UUID = Depends(require_permission("edit", "DEVICES")),
# ):
#     return await auto_discover_modules_by_site(payload, user_id=user_id)


@router.get("/auto_discover_modules_msg")
@router.get("/auto_discover_modules_msg/", include_in_schema=False)
async def api_auto_discover_modules_msg(
    a_name: str = Query(..., alias="a_name"),
    a_type: FrtuDeviceType = Query(..., alias="a_type"),
    user_id: UUID = Depends(require_permission("edit", "DEVICES")),
):
    return await auto_discover_modules_msg(a_name=a_name, a_type=a_type, user_id=user_id)

@router.get("/auto_discover_modules")
async def api_auto_discover_modules_list(
    a_name: str = Query(..., alias="a_name"),
    a_type: FrtuDeviceType = Query(..., alias="a_type"),
    user_id: UUID = Depends(require_permission("edit", "DEVICES")),
):
    return await auto_discover_modules_list(a_name=a_name, a_type=a_type, user_id=user_id)
