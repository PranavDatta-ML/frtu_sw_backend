import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_module_master import FRTUModuleMaster
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_modbus_rtu import ModbusPayload
from src.utils.mb_rtu_ini_builder import handle_modbus_rtu, handle_modbus_tcp, merge_modbus_data
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
    for ch in payload.categoryInfo.channels or []:
        if not ch.id:
            ch.id = uuid4()
        for sl in ch.channelConfig.modbusSlaves or []:
            if not sl.id:
                sl.id = uuid4()
            for p in sl.slaveConfig.modbusParameters or []:
                if not p.id:
                    p.id = uuid4()

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
        ch_no = ch.channelConfig.channelNo
        if str(ch_no) in existing_channels_map:
            existing_ch = existing_channels_map[str(ch_no)]
            
            existing_slaves = {str(sl.get("id")): sl for sl in existing_ch["channelConfig"].get("modbusSlaves", [])}
            new_slaves = []
            
            for slave in ch.channelConfig.modbusSlaves:  
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
                
                for remaining_param in existing_params.values():
                    merged_params.append(remaining_param)
                
                new_slaves.append({
                    "id": slave_id,
                    "status": slave.status,  
                    "slaveConfig": {
                        **slave.slaveConfig.model_dump(exclude={"modbusParameters"}),
                        "modbusParameters": merged_params
                    }
                })
                existing_slaves.pop(slave_id, None)
            
            for remaining_slave in existing_slaves.values():
                new_slaves.append(remaining_slave)
            
            ch_dict = ch.model_dump(mode="json")
            ch_dict["channelConfig"]["modbusSlaves"] = new_slaves
            existing_channels_map[str(ch_no)] = ch_dict
        else:
            existing_channels_map[str(ch_no)] = ch.model_dump(mode="json")

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

    # frtu_client.update_mb_config(payload.model_dump(mode="json"))
    frtu_payload = {
        "categoryInfo": {
            "channels": channel_data["channels"]
        }
    }

    frtu_client.update_mb_config(frtu_payload)

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

    slot_info = attribute.get("slotInfo")
    if not slot_info:
        slot_info = {
            "slotId": str(module.slot_id),
            "slotNumber": getattr(slot, 'name', '3'),
            "cardType": "Modbus"
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
            "channels": channel_data.get("channels", []),
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
