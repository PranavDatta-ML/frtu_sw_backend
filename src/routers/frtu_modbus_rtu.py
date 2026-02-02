from uuid import UUID
from fastapi import APIRouter, Depends, Query
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_modbus_rtu import  ModbusPayload
from src.views.frtu_modbus_rtu import add_or_update_modbus_module, delete_modbus_channel, delete_modbus_parameter, delete_modbus_slave, get_modbus_module_info


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
async def api_get_modbus_module_info(
    device_id: str,
    device_type: str,
    sub_module_id: str | None = None,
    slot_id: str | None = None,
    user_id=Depends(require_permission("view", "MODULE")),
):
    return await get_modbus_module_info(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        slot_id=slot_id,
        user_id=user_id,
    )

@router.delete("/delete_modbus_parameter")
async def api_delete_modbus_parameter(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    parameter_id: str,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_parameter(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        parameter_id=parameter_id,
        user_id=user_id,
    )

@router.delete("/delete_modbus_slave")
async def api_delete_modbus_slave(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    slave_id: str,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_slave(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        slave_id=slave_id,
        user_id=user_id,
    )

@router.delete("/delete_modbus_channel")
async def api_delete_modbus_channel(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    channel_id: str,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_channel(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        channel_id=channel_id,
        user_id=user_id,
    )

