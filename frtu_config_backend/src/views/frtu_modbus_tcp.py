import asyncio
import ipaddress
from uuid import UUID, uuid4
from requests.exceptions import ConnectTimeout, ConnectionError
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_modbus_tcp import ModbusTCPPayload, ModbusTCPResponse
from src.utils.frtu_client import frtu_client

def validate_port(port: str) -> str:
    try:
        if not port or not port.isdigit():
            raise ValueError("Port must be a number")
        port_num = int(port)
        if not (1 <= port_num <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return port
    except ValueError:
        raise ValueError("Invalid port number")

def validate_slot_uuid(slot_id: str) -> UUID:
    try:
        return UUID(slot_id)
    except ValueError:
        raise ValueError("Invalid slotId. Must be valid UUID format")

def validate_unit_id(unit_id: str) -> str:
    try:
        uid = int(unit_id)
        if not (1 <= uid <= 247):
            raise ValueError("Unit ID must be between 1-247")
        return unit_id
    except ValueError:
        raise ValueError("Unit ID must be number 1-247")

def validate_address(addr: str) -> str:
    try:
        a = int(addr)
        if not (0 <= a <= 65535):
            raise ValueError("Modbus address must be 0-65535")
        return addr
    except ValueError:
        raise ValueError("Invalid Modbus address")

def validate_ioa(ioa: str) -> str:
    try:
        i = int(ioa)
        if not (0 <= i <= 9999999999):
            raise ValueError("IOA must be 0-9999999999")
        return ioa
    except ValueError:
        raise ValueError("Invalid IOA value")

def validate_max_count(count: str, max_limit: int, field_name: str, allow_zero: bool = False) -> int:
    try:
        num = int(count)
        if num > max_limit:
            raise ValueError(f"{field_name} cannot exceed {max_limit}")
        if num < 0:
            raise ValueError(f"{field_name} must be ≥ 0")
        if num == 0 and not allow_zero:
            raise ValueError(f"{field_name} cannot be 0")
        return num
    except ValueError:
        raise ValueError(f"{field_name} must be a valid number")

async def add_or_update_modbus_tcp(device_id: str, device_type: str, payload: ModbusTCPPayload, user_id: UUID):
    device_uuid = UUID(device_id)
    device = await FRTUDevices.select(id=device_uuid)
    if not device:
        raise HTTPException(404, "Device not found")

    device = device[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    category = payload.categoryInfo
    
    if payload.moduleType != "COM":
        raise HTTPException(400, "moduleType must be 'COM'")
    # if payload.slotInfo.cardType != "Modbus":
    #     raise HTTPException(400, "slotInfo.cardType must be 'Modbus'")

    try:
        slot_uuid = validate_slot_uuid(payload.slotInfo.slotId)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # if not category.modbusSlaves:
    #     raise HTTPException(400, "At least one slave required")
    
    max_slaves = validate_max_count(category.maxSlaves, 10, "maxSlaves", allow_zero=True)
    if len(category.modbusSlaves) > max_slaves:
        raise HTTPException(400, detail=f"Slaves count ({len(category.modbusSlaves)}) exceeds maxSlaves ({max_slaves})")
    
    for i, slave in enumerate(category.modbusSlaves, 1):
        slave_config = slave.slaveConfig
        
        if not slave_config.name or not slave_config.name.strip():
            raise HTTPException(400, f"Slave {i}: name required")
        
        validate_port(slave_config.port)
        validate_unit_id(slave_config.unitId)
        
        if len(slave_config.accessToken or "") < 4:
            raise HTTPException(400, f"Slave {i}: accessToken ≥4 chars")
        
        max_params = validate_max_count(slave_config.maxParameters, 50, "maxParameters", allow_zero=True)
        if len(slave_config.modbusParameters) > max_params:
            raise HTTPException(400, detail=f"Slave {i} parameters ({len(slave_config.modbusParameters)}) exceeds maxParameters ({max_params})")
        
        # if not slave_config.modbusParameters:
        #     raise HTTPException(400, detail=f"Slave {i} requires at least one parameter")
        
        for j, param in enumerate(slave_config.modbusParameters, 1):
            pc = param.parameterConfig
            
            if not pc.parameterName or not pc.parameterName.strip():
                raise HTTPException(400, f"Slave {i} Param {j}: parameterName required")
            
            validate_address(pc.address)
            
            fc = pc.readFunctionCode
            if fc not in ["1", "2", "3", "4"]:
                raise HTTPException(400, f"Slave {i} Param {j}: readFunctionCode 1,2,3,4")
            
            validate_ioa(pc.ioa)

    for slave in category.modbusSlaves:
        if not slave.id:
            slave.id = str(uuid4())
        for param in slave.slaveConfig.modbusParameters:
            if not param.id:
                param.id = str(uuid4())

    for i, slave in enumerate(category.modbusSlaves, 1):
        try:
            ipaddress.IPv4Address(slave.slaveConfig.ipAddress)
        except:
            raise HTTPException(400, f"Slave {i}: Invalid IPv4 (192.168.2.12)")

    existing_module = await FRTUModules.select(slot_id=slot_uuid)
    existing_slaves = {}

    if existing_module and existing_module[0].channel:
        for sl in existing_module[0].channel.get("tcpSlaves", []):
            existing_slaves[str(sl["id"])] = sl

    merged_slaves = []

    for slave in payload.categoryInfo.modbusSlaves:
        slave_id = str(slave.id) if slave.id else str(uuid4())

        existing_params = {}
        if slave_id in existing_slaves:
            for p in existing_slaves[slave_id]["slaveConfig"]["modbusParameters"]:
                existing_params[str(p["id"])] = p

        merged_params = []

        for param in slave.slaveConfig.modbusParameters:
            param_id = str(param.id) if param.id else str(uuid4())

            param_config = param.parameterConfig.model_dump()
            param_config["readFunctionCode"] = param_config["readFunctionCode"].replace("FC", "")
            dt = param_config["dataType"].upper().replace(" ", "_")
            if not dt.startswith("DT_"):
                dt = f"DT_{dt}"
            param_config["dataType"] = dt
            param_config["endianness"] = param_config["endianness"].replace(" ", "_").upper()

            merged_params.append({
                "id": param_id,
                "status": param.status,
                "parameterConfig": param_config
            })

            existing_params.pop(param_id, None)

        for remaining in existing_params.values():
            merged_params.append(remaining)

        merged_slaves.append({
            "id": slave_id,
            "status": slave.status,
            "slaveConfig": {
                **slave.slaveConfig.model_dump(exclude={"modbusParameters"}),
                "modbusParameters": merged_params
            }
        })

        existing_slaves.pop(slave_id, None)

    for remaining_slave in existing_slaves.values():
        merged_slaves.append(remaining_slave)

    attribute = {
        "slotInfo": payload.slotInfo.model_dump(),
        "modbusCategoryInfo": payload.categoryInfo.model_dump(exclude={"modbusSlaves"}, mode="json")
    }

    channel_data = {"tcpSlaves": merged_slaves}

    if existing_module:
        module_id = existing_module[0].id
        await FRTUModules.update(
            conditions={"id": module_id},
            attribute=attribute,
            channel=channel_data
        )
    else:
        module_type = (await FRTUModuleType.select(name="COM"))[0]
        obj = await FRTUModules.insert(
            slot_id=slot_uuid,
            module_type=module_type.id,
            attribute=attribute,
            channel=channel_data
        )
        module_id = obj.id

    try:
        await asyncio.to_thread(frtu_client.update_mb_tcp_config, {"modbusSlaves": merged_slaves})
    except (ConnectTimeout, ConnectionError):
        raise HTTPException(503, "FRTU device not reachable")

    return {
        "status": "success",
        "moduleId": str(module_id),
        "deviceId": device_id,
        "slaves": len(merged_slaves)
    }

async def get_modbus_tcp_info(
    device_id: str,
    device_type: str,
    sub_module_id: str | None,
    slot_id: str | None,
    user_id,
):
    device_uuid = UUID(device_id)

    device = (await FRTUDevices.select(id=device_uuid))[0]
    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)

    if db_type.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = None

    if sub_module_id:
        modules = await FRTUModules.select(id=UUID(sub_module_id))
        if not modules:
            raise HTTPException(404, "Modbus module not found")
        module = modules[0]

    elif slot_id:
        modules = await FRTUModules.select(slot_id=UUID(slot_id))
        if not modules:
            raise HTTPException(404, "No module found in slot")
        module = modules[0]

    # Fetch slot details (like RTU)
    slot = (await FRTUSlots.select(id=module.slot_id))[0]

    attribute = module.attribute or {}
    channel_data = module.channel or {}

    # FIXED slotInfo: Use slot table + Modbus defaults
    slot_info = attribute.get("slotInfo")
    if not slot_info:
        slot_info = {
            "slotId": str(module.slot_id),           # Real slot UUID
            "slotNumber": getattr(slot, 'name', '3'), # slot.name OR fixed '3'
            "cardType": "Modbus"                     # Fixed for Modbus
        }

    return {
        "status": "success",
        "http_code": 200,
        "message": "Modbus module fetched successfully",
        "module_id": str(module.id),
        "device_id": device_id,
        "slotInfo": slot_info,
        "categoryInfo": {
            **attribute.get("modbusCategoryInfo", {}),
            "modbusSlaves": channel_data.get("tcpSlaves", []),
        },
    }


async def delete_modbus_tcp_parameter(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    parameter_id: str,
    user_id: UUID,
):
    try:
        device_uuid = UUID(device_id)
        module_uuid = UUID(sub_module_id)
        param_uuid = str(UUID(parameter_id))

        device = await FRTUDevices.select(id=device_uuid)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        device = device[0]
        if device.type.name.upper() != device_type.upper():
            raise HTTPException(status_code=400, detail="Device type mismatch")

        modules = await FRTUModules.select(id=module_uuid)
        if not modules:
            raise HTTPException(status_code=404, detail="Module not found")

        module = modules[0]
        channel_data = module.channel or {}
        slaves = channel_data.get("tcpSlaves", [])

        parameter_found = False

        for slave in slaves:
            params = slave.get("slaveConfig", {}).get("modbusParameters", [])
            updated_params = [p for p in params if p.get("id") != param_uuid]

            if len(updated_params) != len(params):
                slave["slaveConfig"]["modbusParameters"] = updated_params
                parameter_found = True

        if not parameter_found:
            raise HTTPException(status_code=404, detail="Parameter ID not found")

        await FRTUModules.update(
            conditions={"id": module_uuid},
            channel={"tcpSlaves": slaves},
        )

        try:
            frtu_payload = {"modbusSlaves": slaves}
            await asyncio.to_thread(frtu_client.update_mb_tcp_config, frtu_payload)
        except Exception:
            raise HTTPException(status_code=503, detail="FRTU device not reachable")

        return {
            "status": "success",
            "message": "Parameter deleted successfully",
            "parameterId": param_uuid,
            "moduleId": str(module_uuid),
            "deviceId": str(device_uuid),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

async def delete_modbus_tcp_slave(device_id: str, device_type: str, sub_module_id: str, slave_id: str, user_id: UUID):
    device_uuid = UUID(device_id)
    module_uuid = UUID(sub_module_id)

    device = await FRTUDevices.select(id=device_uuid)
    if not device:
        raise HTTPException(404, "Device not found")

    device = device[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = await FRTUModules.select(id=module_uuid)
    if not module:
        raise HTTPException(404, "Modbus TCP module not found")

    module = module[0]
    channel_data = module.channel or {}
    slaves = channel_data.get("tcpSlaves", [])

    new_slaves = []
    found = False
    deleted_params = 0

    for sl in slaves:
        if str(sl.get("id")) == slave_id:
            found = True
            deleted_params += len(sl.get("slaveConfig", {}).get("modbusParameters", []))
            continue
        new_slaves.append(sl)

    if not found:
        raise HTTPException(404, "Slave not found")

    await FRTUModules.update(
        conditions={"id": module_uuid},
        channel={"tcpSlaves": new_slaves}
    )

    try:
        await asyncio.to_thread(frtu_client.update_mb_tcp_config, {"modbusSlaves": new_slaves})
    except (ConnectTimeout, ConnectionError):
        raise HTTPException(503, "FRTU device not reachable")

    return {
        "status": "success",
        "deleted_slave_id": slave_id,
        "deleted_parameters_count": deleted_params,
        "remaining_slaves": len(new_slaves)
    }