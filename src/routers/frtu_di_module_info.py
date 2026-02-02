from uuid import UUID
from fastapi import APIRouter, Body, Depends, Query

from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_di_module_info import  ConfigureDIModuleRequest, GetDIModuleRequest
from src.views.frtu_di_do_channel import delete_di_channel
from src.views.frtu_di_module_info import add_di_module_info, delete_di_module, edit_di_module_info, get_di_module_info, get_di_module_info_by_slot_id


router = APIRouter(
    prefix="",
    tags=['frtu_configure_di_channel']
)

@router.post("/add_di_module_info")
async def api_configure_di_channel_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: ConfigureDIModuleRequest  = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_di_module_info(
        device_id=device_id,
        device_type=device_type,
        payload=payload,
        user_id=user_id,
    )

@router.post("/edit_di_module_info")
async def api_move_di_module(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: dict = Body(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await edit_di_module_info(
        device_id=device_id,
        device_type=device_type,
        payload=payload,
        user_id=user_id,
    )


@router.get("/get_di_module_info_by_slot_id")
async def api_get_di_module_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    slot_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_di_module_info_by_slot_id(
        device_id=device_id,
        device_type=device_type,
        slot_id=slot_id,
        user_id=user_id,
    )

@router.get("/get_di_module_info")
async def api_get_di_module_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_di_module_info(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        user_id=user_id,
    )

@router.delete("/delete_di_channel")
async def api_delete_channel(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    channel_id: str = Query(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_di_channel(device_id, device_type, sub_module_id, channel_id, user_id)

@router.delete("/delete_di_module_info")
async def api_delete_di_module(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_di_module(device_id, device_type, sub_module_id, user_id)
