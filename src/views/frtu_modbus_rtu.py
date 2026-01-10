from uuid import UUID, uuid4

from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_modbus_rtu import ModbusPayload
from src.validators.mb_validator import  validate_channels_slaves_params, validate_max_channels, validate_modbus_slot, validate_protocol


def ensure_ids(payload: ModbusPayload):
    for ch in payload.categoryInfo.channels:
        if not ch.id:
            ch.id = uuid4()
        for sl in ch.channelConfig.modbusSlaves:
            if not sl.id:
                sl.id = uuid4()
            for p in sl.slaveConfig.modbusParameters:
                if not p.id:
                    p.id = uuid4()

async def add_or_update_modbus_module(
    device_id: str,
    device_type: str,
    payload: ModbusPayload,
    user_id: UUID,
):
    device_uuid = UUID(device_id)
    device = (await FRTUDevices.select(id=device_uuid))[0]
    validate_modbus_slot(payload.slotInfo.slotNumber)
    validate_protocol(payload.categoryInfo.communicationProtocol)
    validate_max_channels(
    payload.categoryInfo.maxChannels,
    len(payload.categoryInfo.channels)
)

    validate_channels_slaves_params(payload.categoryInfo.channels)

    slots = await FRTUSlots.select(
        id=payload.slotInfo.slotId,
        device_id=device_uuid
    )
    if not slots:
        raise HTTPException(400, "Slot not found for this device")

    slot = slots[0]

    module_types = await FRTUModuleType.select(name="COM")
    if not module_types:
        raise HTTPException(500, "COM module type not configured")

    module_type_id = module_types[0].id

    existing = await FRTUModules.select(slot_id=slot.id)

    ensure_ids(payload)

    attribute = {
        "slotInfo": payload.slotInfo.model_dump(mode="json"),
        "modbusCategoryInfo": payload.categoryInfo.model_dump(
            exclude={"channels"},
            mode="json"
        )
    }

    channel_data = {
        "channels": [
            ch.model_dump(mode="json")
            for ch in payload.categoryInfo.channels
        ]
    }

    if existing:
        module_id = existing[0].id
        await FRTUModules.update(
            conditions={"id": module_id},
            # name=payload.categoryInfo.moduleName,
            attribute=attribute,
            channel=channel_data
        )
    else:
        obj = await FRTUModules.insert(
            slot_id=slot.id,
            # name=payload.categoryInfo.moduleName,
            module_type=module_type_id,
            attribute=attribute,
            channel=channel_data
        )
        module_id = obj.id

    return {
        "status": "success",
        "moduleId": str(module_id)
    }

async def get_modbus_info(
    device_id: UUID,
    device_type: str,
    sub_module_id: UUID,
    user_id: UUID,
):
    # -------- DEVICE VALIDATION --------
    devices = await FRTUDevices.select(id=device_id, device_type=device_type)
    if not devices:
        raise HTTPException(404, "Device not found")

    # -------- MODULE VALIDATION --------
    modules = await FRTUModules.select(id=sub_module_id)
    if not modules:
        raise HTTPException(404, "Module not found")

    module = modules[0]

    # -------- SLOT VALIDATION --------
    slots = await FRTUSlots.select(id=module.slot_id, device_id=device_id)
    if not slots:
        raise HTTPException(
            403,
            "Module does not belong to the given device"
        )

    # -------- RESPONSE --------
    return {
        "status": "success",
        "subModuleId": str(module.id),
        "slotId": str(module.slot_id),
        "attribute": module.attribute,
        "channel": module.channel,
        "createdAt": module.creation_time,
        "updatedAt": module.last_update_time,
    }

