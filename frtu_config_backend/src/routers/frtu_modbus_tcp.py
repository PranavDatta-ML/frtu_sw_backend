from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.middleware.CreatePermissionMiddleware import require_permission
from src.schemas.frtu_modbus_tcp import ModbusTCPPayload
from src.views.frtu_modbus_tcp import add_or_update_modbus_tcp, delete_modbus_tcp_parameter, delete_modbus_tcp_slave, get_modbus_tcp_info


router = APIRouter(tags=["Modbus TCP Module"])

@router.post("/add_modbus_tcp_info")
async def api_add_or_update_modbus_tcp(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: ModbusTCPPayload = ...,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    if len(payload.categoryInfo.modbusSlaves) > int(payload.categoryInfo.maxSlaves):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Number of slaves ({len(payload.categoryInfo.modbusSlaves)}) exceeds maxSlaves ({payload.categoryInfo.maxSlaves})")
    return await add_or_update_modbus_tcp(device_id, device_type, payload, user_id)

@router.get("/get_modbus_tcp_info")
async def api_get_modbus_tcp_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    slot_id: str = Query(...),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    return await get_modbus_tcp_info(device_id, device_type, sub_module_id, slot_id, user_id)

@router.delete("/delete_modbus_tcp_parameter")
async def api_delete_modbus_tcp_parameter(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    parameter_id: str = Query(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_tcp_parameter(
        device_id, device_type, sub_module_id, parameter_id, user_id
    )

@router.delete("/delete_modbus_tcp_slave")
async def api_delete_modbus_tcp_slave(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    slave_id: str,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_tcp_slave(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        slave_id=slave_id,
        user_id=user_id,
    )