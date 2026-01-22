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


