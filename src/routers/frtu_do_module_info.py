from uuid import UUID
from fastapi import APIRouter, Body, Depends, Query

from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_do_module_info import DOModulePayload
from src.views.frtu_do_module_info import add_do_module_info, edit_do_module_info, get_do_module_info


router = APIRouter(
    prefix="",
    tags=['frtu_configure_di_channel']
)

@router.post("/add_do_module_info")
async def api_add_do_module_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: DOModulePayload = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_do_module_info(device_id, device_type, payload, user_id)

@router.get("/get_do_module_info")
async def api_get_do_module_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_do_module_info(device_id, device_type, sub_module_id, user_id)


@router.post("/edit_do_module_info")
async def api_move_do_module(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: dict = Body(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await edit_do_module_info(
        device_id=device_id,
        device_type=device_type,
        payload=payload,
        user_id=user_id,
    )