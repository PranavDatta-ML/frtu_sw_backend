from uuid import UUID
from fastapi import APIRouter, Body, Header, Query, Request, Depends
from src import Settings
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_di_module import ConfigureDIModule, ConfigureDIModuleRequest
from src.views.frtu_di_module import add_di_module, edit_di_module, get_di_module_detail

router = APIRouter(
    prefix="",
    tags=['frtu_configure_di_channel']
)


@router.post("/add_di_general_info")
async def api_add_di_do_module(
    device_id: str = Query(...),
    device_type: str = Query("FRTU"),
    # module_id: UUID = Body(...),
    # module_type: str = Body(...),
    # slot_id: UUID = Body(...),
    payload: ConfigureDIModule = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_di_module(device_id, device_type, payload, user_id)


@router.post("/edit_di_general_info")
async def api_edit_di_do_module(
    device_id: str = Query(...),
    device_type: str = Query("FRTU"),
    payload: ConfigureDIModuleRequest = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await edit_di_module(device_id, device_type, payload, user_id)

@router.get("/get_di_general_info")
async def api_get_di_do_module_detail(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_di_module_detail(device_id, device_type, sub_module_id, user_id)



