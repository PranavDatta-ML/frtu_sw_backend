from uuid import UUID
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.validators.mb_rtu_tcp import _delete_rtu_parameter, _delete_rtu_slave, _delete_tcp_parameter, _delete_tcp_slave


async def delete_modbus_parameter_unified(device_id: str, device_type: str, sub_module_id: str, parameter_id: str, user_id: UUID):
    device = await FRTUDevices.select(id=UUID(device_id))
    if not device:
        raise HTTPException(404, "Device not found")
    device = device[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = await FRTUModules.select(id=UUID(sub_module_id))
    if not module:
        raise HTTPException(404, "Module not found")

    module = module[0]

    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "COM":
        raise HTTPException(400, "Only COM module supports Modbus")

    protocol = module.attribute.get("modbusCategoryInfo", {}).get("communicationProtocol", "Modbus RTU").upper()

    if protocol == "MODBUS RTU":
        return await _delete_rtu_parameter(module, parameter_id)

    else:
        return await _delete_tcp_parameter(module, parameter_id)

    # raise HTTPException(400, "Unknown Modbus protocol")

async def delete_modbus_slave_unified(device_id: str, device_type: str, sub_module_id: str, slave_id: str, user_id: UUID):
    device = await FRTUDevices.select(id=UUID(device_id))
    if not device:
        raise HTTPException(404, "Device not found")

    device = device[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = await FRTUModules.select(id=UUID(sub_module_id))
    if not module:
        raise HTTPException(404, "Module not found")

    module = module[0]

    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "COM":
        raise HTTPException(400, "Only COM module supports Modbus")

    protocol = module.attribute.get("modbusCategoryInfo", {}).get("communicationProtocol", "Modbus RTU").upper()

    if protocol == "MODBUS RTU":
        return await _delete_rtu_slave(module, slave_id)

    else:
        return await _delete_tcp_slave(module, slave_id)

    # raise HTTPException(400, "Unknown Modbus protocol")
