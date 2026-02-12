from typing import Optional, Union
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from src.middleware.CreatePermissionMiddleware import require_permission
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_modbus_rtu import ModbusPayload
from src.schemas.frtu_modbus_rtu_tcp import UnifiedModbusPayload
from src.schemas.frtu_modbus_tcp import ModbusTCPPayload
from src.views.frtu_modbus_rtu import add_or_update_modbus_module, get_modbus_module_info
from src.views.frtu_modbus_rtu_tcp import delete_modbus_parameter_unified, delete_modbus_slave_unified
from src.views.frtu_modbus_tcp import add_or_update_modbus_tcp, get_modbus_tcp_info

router = APIRouter(tags=["Modbus Module"])

@router.post("/add_modbus_info")
async def api_add_modbus_info(
    device_id: str = Query(...),
    device_type: str = Query(...),
    payload: dict = Body(...),  # Raw JSON!
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    protocol = payload.get("categoryInfo", {}).get("communicationProtocol", "").upper()
    
    if protocol == "MODBUS RTU":
        # FIX: Convert slotId str → UUID for RTU query
        payload["slotInfo"]["slotId"] = str(UUID(payload["slotInfo"]["slotId"]))
        rtu_payload = ModbusPayload(**payload)
        return await add_or_update_modbus_module(device_id, device_type, rtu_payload, user_id)
    
    elif protocol == "MODBUS TCP":
        tcp_payload = ModbusTCPPayload(**payload)
        return await add_or_update_modbus_tcp(device_id, device_type, tcp_payload, user_id)
    
    else:
        raise HTTPException(400, "Use 'Modbus RTU' or 'Modbus TCP'")
    
@router.get("/get_modbus_info")
async def api_get_modbus_info(
    device_id: str = Query(..., description="Device UUID"),
    device_type: str = Query(..., description="Device type (FRTU)"),
    sub_module_id: Optional[str] = Query(None, description="Module UUID (optional)"),
    slot_id: Optional[str] = Query(None, description="Slot UUID (required if no sub_module_id)"),
    user_id: UUID = Depends(require_permission("view", "MODULE")),
):
    # if not sub_module_id and not slot_id:
    #     raise HTTPException(400, "sub_module_id OR slot_id is required")
    # if sub_module_id and slot_id:
    #     raise HTTPException(400, "Provide ONLY ONE: sub_module_id OR slot_id")
    
    try:
        device_uuid = UUID(device_id)
        slot_uuid = UUID(slot_id) if slot_id else None
        module_uuid = UUID(sub_module_id) if sub_module_id else None
        
        device = (await FRTUDevices.select(id=device_uuid))[0]
        if device.type.name.strip().upper() != device_type.strip().upper():
            raise HTTPException(400, f"Device type mismatch. Expected: {device.type.name}")
        
        if slot_uuid:
            slots = await FRTUSlots.select(id=slot_uuid, device_id=device_uuid)
            if not slots:
                raise HTTPException(404, f"Slot {slot_uuid} not found in device {device_id}")
        
        if module_uuid:
            modules = await FRTUModules.select(id=module_uuid)
            if not modules or modules[0].slot_id not in [device_uuid, slot_uuid]:
                raise HTTPException(404, f"Module {module_uuid} not found in device {device_id}")
        
        module = (await FRTUModules.select(
            id=module_uuid if module_uuid else None,
            slot_id=slot_uuid if slot_uuid else None
        ))[0]
        
        attribute = module.attribute or {}
        protocol = attribute.get("modbusCategoryInfo", {}).get("communicationProtocol", "Modbus RTU").upper()  
        
        if protocol == "MODBUS TCP":
            if not sub_module_id or not slot_id:
                raise HTTPException(400, "TCP requires both sub_module_id & slot_id")
            return await get_modbus_tcp_info(device_id, device_type, sub_module_id, slot_id, user_id)
        else:
            return await get_modbus_module_info(device_id, device_type, sub_module_id, slot_id, user_id)
            
    except ValueError:
        raise HTTPException(400, "Invalid UUID format")
    except IndexError:
        raise HTTPException(404, "Module/Slot/Device not found")

@router.delete("/delete_modbus_parameter")
async def delete_parameter(
    device_id: str = Query(...),
    device_type: str = Query(...),
    sub_module_id: str = Query(...),
    parameter_id: str = Query(...),
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_parameter_unified(
        device_id, device_type, sub_module_id, parameter_id, user_id
    )


@router.delete("/delete_modbus_slave")
async def api_delete_modbus_slave(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    slave_id: str,
    user_id: UUID = Depends(require_permission("edit", "MODULE")),
):
    return await delete_modbus_slave_unified(
        device_id=device_id,
        device_type=device_type,
        sub_module_id=sub_module_id,
        slave_id=slave_id,
        user_id=user_id,
    )
