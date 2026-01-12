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

async def get_modbus_info(device_id: str, device_type: str, sub_module_id: UUID, user_id: UUID):
    device_uuid = UUID(device_id)
    
    device = (await FRTUDevices.select(id=device_uuid))[0]
    if device.type.name.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=sub_module_id)
    if not modules:
        raise HTTPException(404, "Modbus module not found")

    module = modules[0]

    slots = await FRTUSlots.select(id=module.slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(403, "Module does not belong to this device")

    return {
        "status": "success",
        "moduleId": str(module.id),
        "moduleType": "COM",
        "slotId": str(module.slot_id),
        "slotNumber": slots[0].name,
        "attribute": module.attribute,
        "channels": module.channel.get("channels", []),
        "channelsCount": len(module.channel.get("channels", []))
    }


