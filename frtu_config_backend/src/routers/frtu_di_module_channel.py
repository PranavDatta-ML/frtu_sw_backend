from uuid import UUID
from fastapi import APIRouter, Body, Depends, Query

from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_di_module import AddDIChannelPayload, ConfigureModuleIOARequest, ConfigureSingleDIChannelRequest
from src.views.frtu_configure_di_channel import add_di_channel, configure_di_channel_info_func, configure_module_ioa, get_di_channel_detail, get_di_channel_list

router = APIRouter(
    prefix="",
    tags=['frtu_configure_di_channel']
)

@router.post("/add_di_channel")
async def api_add_di_channel(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: AddDIChannelPayload = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_di_channel(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=payload.sub_module_id,
        channel_no=payload.channel_no,
        user_id=user_id,
    )

@router.get("/get_di_channel")
async def api_get_di_channel(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: UUID = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_di_channel_list(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        user_id=user_id,
    )


# @router.post("/configure_di_channel_info")
# async def api_configure_di_channel_info(
#     device_id: str = Query(...),
#     device_type: str = Query(...),
#     payload: ConfigureSingleDIChannelRequest = ...,
#     user_id: UUID = Depends(require_permission("edit", "MODULE")),
# ):
#     return await configure_di_channel_info_func(device_id, device_type, payload, user_id)

@router.get("/get_di_channel_info")
async def api_get_di_channel_detail(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    channel_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_di_channel_detail(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        channel_id=channel_id,
        user_id=user_id,
    )

@router.post("/configure_module_ioa")
async def api_configure_module_ioa(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: ConfigureModuleIOARequest = Body(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await configure_module_ioa(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=payload.sub_module_id,
        base_ioa=payload.base_ioa,
        channels=payload.channels,
        user_id=user_id,
    )
