from uuid import UUID
from fastapi import APIRouter, Depends, Query
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_modbus_rtu import  ModbusPayload
from src.views.frtu_modbus_rtu import add_or_update_modbus_module, get_modbus_info


router = APIRouter(tags=["Modbus Module"])

@router.post("/add_modbus_info")
async def api_add_modbus_module(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: ModbusPayload = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await add_or_update_modbus_module(
        device_id,
        device_type,
        payload,
        user_id
    )

@router.get("/get_modbus_info")
async def api_get_modbus_info(
    device_id: UUID = Query(...),
    device_type: str = Query(...),
    sub_module_id: UUID = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_modbus_info(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        user_id=user_id,
    )