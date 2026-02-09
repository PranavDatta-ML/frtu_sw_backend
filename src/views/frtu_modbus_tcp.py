import asyncio
from uuid import UUID, uuid4
from requests.exceptions import ConnectTimeout, ConnectionError
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
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

def validate_max_count(count: str, max_limit: int, field_name: str) -> int:
    try:
        num = int(count)
        if num > max_limit:
            raise ValueError(f"{field_name} cannot exceed {max_limit}")
        if num < 1:
            raise ValueError(f"{field_name} must be at least 1")
        return num
    except ValueError:
        raise ValueError(f"{field_name} must be a valid number")

# async def add_or_update_modbus_tcp(device_id: str, device_type: str, payload: ModbusTCPPayload, user_id: UUID):
#     try:
#         device_uuid = UUID(device_id)
#         device = await FRTUDevices.select(id=device_uuid)
#         if not device:
#             raise HTTPException(status_code=404, detail="Device not found")

#         device = device[0]
#         if device.type.name.upper() != device_type.upper():
#             raise HTTPException(status_code=400, detail=f"Device type mismatch. Expected: {device.type.name}")

#         category = payload.categoryInfo
#         if not category.modbusSlaves:
#             raise HTTPException(status_code=400, detail="At least one TCP slave required")

#         slot_uuid = validate_slot_uuid(payload.slotInfo.slotId)
#         max_slaves = validate_max_count(category.maxSlaves, 10, "maxSlaves")
#         if len(category.modbusSlaves) > max_slaves:
#             raise HTTPException(status_code=400, detail=f"Slaves count ({len(category.modbusSlaves)}) exceeds maxSlaves ({max_slaves})")

#         slaves = category.modbusSlaves
#         for i, slave in enumerate(slaves):
#             if not slave.slaveConfig.name or len(slave.slaveConfig.name.strip()) == 0:
#                 raise HTTPException(status_code=400, detail=f"Slave {i+1} name is required")
        
#             validate_port(slave.slaveConfig.port)
#             validate_unit_id(slave.slaveConfig.unitId)
            
#             if not slave.slaveConfig.accessToken or len(slave.slaveConfig.accessToken) < 4:
#                 raise HTTPException(status_code=400, detail=f"Slave {i+1} accessToken must be at least 4 characters")
            
#             max_params = validate_max_count(slave.slaveConfig.maxParameters, 50, "maxParameters")
#             if len(slave.slaveConfig.modbusParameters) > max_params:
#                 raise HTTPException(status_code=400, detail=f"Slave {i+1} parameters ({len(slave.slaveConfig.modbusParameters)}) exceeds maxParameters ({max_params})")
            
#             if not slave.slaveConfig.modbusParameters:
#                 raise HTTPException(status_code=400, detail=f"Slave {i+1} requires at least one parameter")

#             for j, param in enumerate(slave.slaveConfig.modbusParameters):
#                 pc = param.parameterConfig
#                 if not pc.parameterName or len(pc.parameterName.strip()) == 0:
#                     raise HTTPException(status_code=400, detail=f"Slave {i+1} Parameter {j+1} parameterName is required")
                
#                 validate_address(pc.address)
#                 if not pc.readFunctionCode or pc.readFunctionCode not in ['1', '2', '3', '4']:
#                     raise HTTPException(status_code=400, detail=f"Slave {i+1} Parameter {j+1} readFunctionCode must be 1,2,3 or 4")
                
#                 validate_ioa(pc.ioa)

#         for slave in slaves:
#             slave.id = slave.id or str(uuid4())
#             for param in slave.slaveConfig.modbusParameters:
#                 param.id = param.id or str(uuid4())
#                 param_config = param.parameterConfig.model_dump()
#                 param_config["readFunctionCode"] = param_config["readFunctionCode"].replace("FC", "")
#                 dt = param_config["dataType"].upper().replace(" ", "_")
#                 if not dt.startswith("DT_"):
#                     dt = f"DT_{dt}"
#                 param_config["dataType"] = dt
#                 param_config["endianness"] = param_config["endianness"].replace(" ", "_").upper()
#                 param.parameterConfig = param_config

#         attribute = {
#             "slotInfo": payload.slotInfo.model_dump(),
#             "protocol": "TCP"
#         }

#         channel_data = {"tcpSlaves": [s.model_dump(mode="json") for s in slaves]}

#         existing = await FRTUModules.select(slot_id=slot_uuid)
#         if existing:
#             module_id = existing[0].id
#             await FRTUModules.update(
#                 conditions={"id": module_id},
#                 attribute=attribute,
#                 channel=channel_data
#             )
#             operation = "updated"
#         else:
#             module_types = await FRTUModuleType.select(name="COM")
#             if not module_types:
#                 raise HTTPException(status_code=404, detail="COM module type not found in database")
            
#             module_type = module_types[0]
#             obj = await FRTUModules.insert(
#                 slot_id=slot_uuid,
#                 module_type=module_type.id,
#                 attribute=attribute,
#                 channel=channel_data
#             )
#             module_id = obj.id
#             operation = "created"

#         try:
#             frtu_payload = {"modbusSlaves": channel_data["tcpSlaves"]}
#             await asyncio.to_thread(frtu_client.update_mb_tcp_config, frtu_payload)
#         except (ConnectTimeout, ConnectionError):
#             raise HTTPException(
#                 status_code=503,
#                 detail={"msg": "FRTU device is not reachable. Please check device power or network."}
#             )

#         return {
#             "status": "success",
#             "message": f"Modbus TCP module {operation} successfully for device {device_id}",
#             "moduleId": str(module_id),
#             "deviceId": device_id,
#             "slaves": len(slaves)
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

async def add_or_update_modbus_tcp(device_id: str, device_type: str, payload: ModbusTCPPayload, user_id: UUID):
    device_uuid = UUID(device_id)
    device = await FRTUDevices.select(id=device_uuid)
    if not device:
        raise HTTPException(404, "Device not found")

    device = device[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    slot_uuid = UUID(payload.slotInfo.slotId)

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
        "protocol": "TCP"
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

async def get_modbus_tcp_info(device_id: str, device_type: str, sub_module_id: str, slot_id: str, user_id: UUID):
    try:
        try:
            device_uuid = UUID(device_id)
            slot_uuid = UUID(slot_id)
            module_uuid = UUID(sub_module_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format in request")

        device = await FRTUDevices.select(id=device_uuid)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        device = device[0]
        if device.type.name.upper() != device_type.upper():
            raise HTTPException(status_code=400, detail=f"Device type mismatch. Expected {device.type.name}")

        module = await FRTUModules.select(id=module_uuid, slot_id=slot_uuid)
        if not module:
            raise HTTPException(status_code=404, detail="Modbus TCP module not found for this slot")

        module = module[0]

        module_type = await FRTUModuleType.select(id=module.module_type)
        if not module_type:
            raise HTTPException(status_code=404, detail="Module type not found")

        module_type_name = module_type[0].name

        attribute = module.attribute or {}
        channel = module.channel or {}

        slot_info = attribute.get("slotInfo")
        if not slot_info:
            raise HTTPException(status_code=500, detail="Slot information missing in module")

        tcp_slaves = channel.get("tcpSlaves", [])

        if not tcp_slaves:
            raise HTTPException(status_code=404, detail="No Modbus TCP slaves configured in this module")

        first_slave = tcp_slaves[0]
        category_info = {
            "moduleId": attribute.get("moduleId", "PR-UNKNOWN"),
            "moduleName": attribute.get("moduleName", "Modbus TCP"),
            "categoryDescription": attribute.get("categoryDescription"),
            "communicationProtocol": "Modbus TCP",
            "hardwareVersion": attribute.get("hardwareVersion", "1.0"),
            "firmwareVersion": attribute.get("firmwareVersion", "1.0"),
            "maxSlaves": str(len(tcp_slaves)),
            "modbusSlaves": tcp_slaves
        }

        response = ModbusTCPResponse(
            status="success",
            moduleId=str(module.id),
            moduleType=module_type_name,
            deviceId=str(device.id),
            slotInfo=slot_info,
            categoryInfo=category_info
        )

        return response.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

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