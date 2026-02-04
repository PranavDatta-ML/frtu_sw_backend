from uuid import UUID, uuid4

from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_module_master import FRTUModuleMaster
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_modbus_rtu import ModbusPayload
from src.validators.mb_validator import  validate_channels_slaves_params, validate_max_channels, validate_modbus_slot, validate_protocol
from src.utils.frtu_client import frtu_client

async def push_full_modbus_config_to_frtu(module: FRTUModules):
    slot = (await FRTUSlots.select(id=module.slot_id))[0]

    attribute = module.attribute or {}
    channel_data = module.channel or {}

    full_payload = {
        "slot_number": 3,
        "modbus_data": {
            "slotInfo": attribute.get("slotInfo"),
            "categoryInfo": {
                **attribute.get("modbusCategoryInfo", {}),
                "channels": channel_data.get("channels", []),
            },
        },
    }

    frtu_client.update_mb_config(full_payload["modbus_data"])

def ensure_ids(payload: ModbusPayload):
    for ch in payload.categoryInfo.channels:
        ch.id = ch.id or uuid4()
        for sl in ch.channelConfig.modbusSlaves:
            sl.id = sl.id or uuid4()
            for p in sl.slaveConfig.modbusParameters:
                p.id = p.id or uuid4()

async def add_or_update_modbus_module(device_id: str, device_type: str, payload: ModbusPayload, user_id: UUID):
    device_uuid = UUID(device_id)
    device = (await FRTUDevices.select(id=device_uuid))[0]

    if device.type.name.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type mismatch")

    validate_modbus_slot(payload.slotInfo.slotNumber)

    module_types = await FRTUModuleType.select(name=payload.moduleType)
    if not module_types:
        raise HTTPException(400, f"Module type '{payload.moduleType}' not configured")

    validate_protocol(payload.categoryInfo.communicationProtocol)
    validate_max_channels(payload.categoryInfo.maxChannels, len(payload.categoryInfo.channels))
    validate_channels_slaves_params(payload.categoryInfo.channels)

    slots = await FRTUSlots.select(id=payload.slotInfo.slotId, device_id=device_uuid)
    if not slots:
        raise HTTPException(400, "Slot not found for this device")
    slot = slots[0]

    ensure_ids(payload)

    attribute = {
        "slotInfo": payload.slotInfo.model_dump(mode="json"),
        "modbusCategoryInfo": payload.categoryInfo.model_dump(exclude={"channels"}, mode="json")
    }

    existing = await FRTUModules.select(slot_id=slot.id)

    existing_channels_map = {}
    if existing and existing[0].channel:
        for ch in existing[0].channel.get("channels", []):
            ch_no = ch.get("channelConfig", {}).get("channelNo")
            if ch_no:
                existing_channels_map[str(ch_no)] = ch

    for ch in payload.categoryInfo.channels:
        ch_dict = ch.model_dump(mode="json")
        ch_no = ch_dict["channelConfig"]["channelNo"]
        existing_channels_map[str(ch_no)] = ch_dict

    channel_data = {"channels": list(existing_channels_map.values())}

    if existing:
        module_id = existing[0].id
        await FRTUModules.update(
            conditions={"id": module_id},
            attribute=attribute,
            channel=channel_data
        )
    else:
        obj = await FRTUModules.insert(
            slot_id=slot.id,
            module_type=module_types[0].id,
            attribute=attribute,
            channel=channel_data
        )
        module_id = obj.id

    frtu_client.update_mb_config(payload.model_dump(mode="json"))

    return {"status": "success", "moduleId": str(module_id)}

async def get_modbus_module_info(
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

    if not sub_module_id and not slot_id:
        raise HTTPException(400, "sub_module_id or slot_id is required")

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

    # module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    # if module_type.name.upper() != "MODBUS":
    #     raise HTTPException(400, "Module is not Modbus")

    slot = (await FRTUSlots.select(id=module.slot_id))[0]

    attribute = module.attribute or {}
    channel_data = module.channel or {}

    return {
        "status": "success",
        "http_code": 200,
        "message": "Modbus module fetched successfully",
        "data": {
            "module_id": str(module.id),
            "device_id": device_id,
            "slot_id": str(slot.id),
            "slot_number": slot.name,
            # "module_type": module_type.name,
            "slotInfo": attribute.get("slotInfo"),
            "categoryInfo": {
                **attribute.get("modbusCategoryInfo", {}),
                "channels": channel_data.get("channels", []),
            },
        },
    }

async def delete_modbus_parameter(device_id: str, device_type: str, sub_module_id: str, parameter_id: str, user_id):
    device = (await FRTUDevices.select(id=UUID(device_id)))[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = (await FRTUModules.select(id=UUID(sub_module_id)))[0]
    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "COM":
        raise HTTPException(400, "Only COM module supports Modbus")

    channels = module.channel.get("channels", [])
    found = False

    for ch in channels:
        ch_no = ch["channelConfig"]["channelNo"]
        slaves = ch["channelConfig"].get("modbusSlaves", [])

        for s_idx, sl in enumerate(slaves, start=1):
            params = sl["slaveConfig"].get("modbusParameters", [])

            for p_idx, p in enumerate(params, start=1):
                if str(p["id"]) == parameter_id:
                    frtu_client.delete_modbus_param(ch_no, s_idx, p_idx)
                    params.pop(p_idx - 1)
                    found = True
                    break
            if found:
                break
        if found:
            break

    if not found:
        raise HTTPException(404, "Parameter not found")

    await FRTUModules.update(conditions={"id": module.id}, channel={"channels": channels})

    return {"status": "success", "message": "Parameter deleted from DB and mb_config.ini"}

async def delete_modbus_slave(device_id: str, device_type: str, sub_module_id: str, slave_id: str, user_id):
    device = (await FRTUDevices.select(id=UUID(device_id)))[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = (await FRTUModules.select(id=UUID(sub_module_id)))[0]
    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "COM":
        raise HTTPException(400, "Only COM module supports Modbus")

    channels = module.channel.get("channels", [])
    found = False

    for ch in channels:
        ch_no = ch["channelConfig"]["channelNo"]
        slaves = ch["channelConfig"].get("modbusSlaves", [])

        for s_idx, sl in enumerate(slaves, start=1):
            if str(sl["id"]) == slave_id:
                frtu_client.delete_modbus_slave(ch_no, s_idx)
                slaves.pop(s_idx - 1)
                found = True
                break
        if found:
            break

    if not found:
        raise HTTPException(404, "Slave not found")

    await FRTUModules.update(conditions={"id": module.id}, channel={"channels": channels})

    return {"status": "success", "message": "Slave and its parameters deleted from DB and mb_config.ini"}

async def delete_modbus_channel(device_id: str, device_type: str, sub_module_id: str, channel_id: str, user_id):
    device = (await FRTUDevices.select(id=UUID(device_id)))[0]
    if device.type.name.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = (await FRTUModules.select(id=UUID(sub_module_id)))[0]
    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "COM":
        raise HTTPException(400, "Only COM module supports Modbus")

    channels = module.channel.get("channels", [])
    found = False

    for idx, ch in enumerate(channels, start=1):
        if str(ch["id"]) == channel_id:
            ch_no = ch["channelConfig"]["channelNo"]
            frtu_client.delete_modbus_channel(ch_no)
            channels.pop(idx - 1)
            found = True
            break

    if not found:
        raise HTTPException(404, "Channel not found")

    await FRTUModules.update(conditions={"id": module.id}, channel={"channels": channels})

    return {"status": "success", "message": "Channel, slaves and parameters deleted from DB and mb_config.ini"}


# async def delete_modbus_parameter(
#     device_id: str,
#     device_type: str,
#     sub_module_id: str,
#     parameter_id: str,
#     user_id,
# ):
#     device_uuid = UUID(device_id)
#     module_uuid = UUID(sub_module_id)

#     devices = await FRTUDevices.select(id=device_uuid)
#     if not devices:
#         raise HTTPException(404, "Device not found")

#     device = devices[0]
#     db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
#     if db_type.upper() != device_type.upper():
#         raise HTTPException(400, "Device type mismatch")

#     modules = await FRTUModules.select(id=module_uuid)
#     if not modules:
#         raise HTTPException(404, "Modbus module not found")

#     module = modules[0]

#     module_type = (await FRTUModuleType.select(id=module.module_type))[0]
#     if module_type.name.upper() != "COM":
#         raise HTTPException(400, "Only Modbus COM module supports parameter delete")

#     channel_data = module.channel or {}
#     channels = channel_data.get("channels", [])

#     found = False

#     for ch in channels:
#         slaves = ch.get("channelConfig", {}).get("modbusSlaves", [])
#         for sl in slaves:
#             params = sl.get("slaveConfig", {}).get("modbusParameters", [])
#             new_params = []
#             for p in params:
#                 if str(p.get("id")) == parameter_id:
#                     found = True
#                     continue
#                 new_params.append(p)
#             sl["slaveConfig"]["modbusParameters"] = new_params

#     if not found:
#         raise HTTPException(404, "Parameter not found")

#     await FRTUModules.update(
#         conditions={"id": module_uuid},
#         channel={"channels": channels},
#     )

#     payload = {
#         "categoryInfo": {
#             "channels": channels
#         }
#     }

#     frtu_client.update_mb_config(payload)

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "Modbus parameter deleted successfully",
#         "deleted_parameter_id": parameter_id,
#     }

# async def delete_modbus_slave(
#     device_id: str,
#     device_type: str,
#     sub_module_id: str,
#     slave_id: str,
#     user_id,
# ):
#     device_uuid = UUID(device_id)
#     module_uuid = UUID(sub_module_id)

#     devices = await FRTUDevices.select(id=device_uuid)
#     if not devices:
#         raise HTTPException(404, "Device not found")

#     device = devices[0]
#     db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
#     if db_type.upper() != device_type.upper():
#         raise HTTPException(400, "Device type mismatch")

#     modules = await FRTUModules.select(id=module_uuid)
#     if not modules:
#         raise HTTPException(404, "Modbus module not found")

#     module = modules[0]

#     module_type = (await FRTUModuleType.select(id=module.module_type))[0]
#     if module_type.name.upper() != "COM":
#         raise HTTPException(400, "Slave delete allowed only for Modbus COM module")

#     channel_data = module.channel or {}
#     channels = channel_data.get("channels", [])

#     found = False
#     deleted_params = 0

#     for ch in channels:
#         slaves = ch.get("channelConfig", {}).get("modbusSlaves", [])
#         new_slaves = []

#         for sl in slaves:
#             if str(sl.get("id")) == slave_id:
#                 found = True
#                 deleted_params += len(sl.get("slaveConfig", {}).get("modbusParameters", []))
#                 continue
#             new_slaves.append(sl)

#         ch["channelConfig"]["modbusSlaves"] = new_slaves

#     if not found:
#         raise HTTPException(404, "Slave not found in this Modbus module")

#     await FRTUModules.update(
#         conditions={"id": module_uuid},
#         channel={"channels": channels},
#     )
#     updated_module = (await FRTUModules.select(id=module_uuid))[0]
#     await push_full_modbus_config_to_frtu(updated_module)

#     payload = {
#         "categoryInfo": {
#             "channels": channels
#         }
#     }

#     frtu_client.update_mb_config(payload)

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "Modbus slave and all its parameters deleted successfully",
#         "deleted_slave_id": slave_id,
#         "deleted_parameters_count": deleted_params,
#     }

# async def delete_modbus_channel(
#     device_id: str,
#     device_type: str,
#     sub_module_id: str,
#     channel_id: str,
#     user_id,
# ):
#     device_uuid = UUID(device_id)
#     module_uuid = UUID(sub_module_id)

#     devices = await FRTUDevices.select(id=device_uuid)
#     if not devices:
#         raise HTTPException(404, "Device not found")

#     device = devices[0]
#     db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
#     if db_type.upper() != device_type.upper():
#         raise HTTPException(400, "Device type mismatch")

#     modules = await FRTUModules.select(id=module_uuid)
#     if not modules:
#         raise HTTPException(404, "Modbus module not found")

#     module = modules[0]

#     module_type = (await FRTUModuleType.select(id=module.module_type))[0]
#     if module_type.name.upper() != "COM":
#         raise HTTPException(400, "Channel delete allowed only for Modbus COM module")

#     channel_data = module.channel or {}
#     channels = channel_data.get("channels", [])

#     new_channels = []
#     found = False
#     deleted_slaves = 0
#     deleted_params = 0

#     for ch in channels:
#         if str(ch.get("id")) == channel_id:
#             found = True
#             slaves = ch.get("channelConfig", {}).get("modbusSlaves", [])
#             deleted_slaves += len(slaves)

#             for sl in slaves:
#                 deleted_params += len(sl.get("slaveConfig", {}).get("modbusParameters", []))
#             continue

#         new_channels.append(ch)

#     if not found:
#         raise HTTPException(404, "Channel not found in this Modbus module")

#     await FRTUModules.update(
#         conditions={"id": module_uuid},
#         channel={"channels": new_channels},
#     )

#     payload = {
#         "categoryInfo": {
#             "channels": new_channels
#         }
#     }

#     # frtu_client.update_mb_config(payload)

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "Modbus channel, its slaves, and parameters deleted successfully",
#         "deleted_channel_id": channel_id,
#         "deleted_slaves_count": deleted_slaves,
#         "deleted_parameters_count": deleted_params,
#         "remaining_channels": len(new_channels),
#     }

