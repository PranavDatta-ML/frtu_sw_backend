import asyncio
import uuid
from typing import Any, Dict
from uuid import UUID, uuid4
from fastapi import HTTPException

from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_do_module_info import DOModulePayload
from src.utils.do_ini_builder import clear_do_ini_slot, update_do_ini_for_module
from src.utils.frtu_client import frtu_client
from src.validators.di_do_name_validator import validate_unique_module_name
from src.validators.do_channel_validator import enforce_do_rules, normalize_do_channel, normalize_do_dp_associations, normalize_do_dp_associations, validate_do_channels, validate_do_channels_strict

async def add_do_module_info(
    device_id: str,
    device_type: str,
    payload: DOModulePayload,
    user_id: UUID,
) -> Dict[str, Any]:

    device_uuid = UUID(device_id)

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(404, "Device not found")
    device = devices[0]

    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type mismatch")

    if payload.module_type.upper() != "DO":
        raise HTTPException(400, "Only DO modules supported")

    slots = await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(400, "Invalid slot_id")
    slot = slots[0]

    slot_number = int(slot.name)
    if slot_number < 4:
        raise HTTPException(400, "DO allowed only from slot 4 onwards")
    do_types = await FRTUModuleType.select(name="DO")
    if not do_types:
        raise HTTPException(500, "DO module type not configured")
    do_type_id = do_types[0].id

    existing_modules = await FRTUModules.select(slot_id=payload.slot_id)

    info_key = "module_do_info"
    general_info: Dict[str, Any] = {}
    channel_blob: Dict[str, Any] = {"channels": {}}
    module_id = None

    if existing_modules:
        module = existing_modules[0]
        if module.module_type != do_type_id:
            raise HTTPException(400, "Slot occupied by another module type")

        module_id = module.id
        general_info = dict(
            module.attribute.get(info_key, {}).get("general_info", {})
        )
        channel_blob = dict(module.channel or {"channels": {}})

    if payload.general_info:
        general_info.update(payload.general_info)

    general_info.update({
        "slot_number": slot_number,
        "slot_id": str(payload.slot_id),
        "module_name": "Digital Output",
        "module_type": "DO",
    })
    module_display_name = general_info.get("name")
    await validate_unique_module_name(
        device_id=device_uuid,
        module_type_name="DO",
        module_name=module_display_name,
        current_module_id=module_id,
    )

    existing_channels = channel_blob.get("channels", {})
    updated_channels = dict(existing_channels)

    for ch in payload.channels or []:
        ch_no = str(int(ch.channelNoPrimary))
        key = f"channel_{ch_no}"

        incoming = ch.dict(exclude={"channelNoPrimary"})
        incoming_channel_id = incoming.get("channelId")

        if incoming_channel_id:
            channel_id = incoming_channel_id
        else:
            channel_id = (
                existing_channels.get(key, {}).get("channelId")
                or str(uuid4())
            )

        incoming["channelId"] = channel_id
        incoming["channelNo"] = ch_no
        incoming["channelNoPrimary"] = ch_no

        updated_channels[key] = {
            **existing_channels.get(key, {}),
            **incoming,
        }

    enforce_do_rules(updated_channels)
    validate_do_channels_strict(updated_channels)
    normalize_do_dp_associations(updated_channels)

    channel_blob["channels"] = updated_channels

    attribute = {
        "device_id": str(device_uuid),
        "slot_number": slot_number,
        info_key: {"general_info": general_info},
    }

    if module_id:
        await FRTUModules.update(
            conditions={"id": module_id},
            name="Digital Output",
            module_type=do_type_id,
            attribute=attribute,
            channel=channel_blob,
        )
        message = "DO module updated successfully"
    else:
        module = await FRTUModules.insert(
            slot_id=payload.slot_id,
            name="Digital Output",
            module_type=do_type_id,
            attribute=attribute,
            channel=channel_blob,
        )
        module_id = module.id
        message = "DO module created successfully"

    await asyncio.to_thread(
        frtu_client.update_devids_conf,
        slot_number,
        "DO",
    )

    serial_number = (
        general_info.get("serialNumber") 
        or general_info.get("serial_number")
    )
    if serial_number:
        await asyncio.to_thread(
            update_do_ini_for_module,
            serial_number,
            slot_number,
            updated_channels,
        )

    return {
        "status": "success",
        "http_code": 200,
        "message": message,
        "data": {
            "module_id": str(module_id),
            "slot_number": slot_number,
            "configured_channels": len(updated_channels),
        },
    }


async def get_do_module_info(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    user_id: UUID,
    ) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
        module_uuid = UUID(sub_module_id)
    except Exception:
        raise HTTPException(400, "Invalid UUID format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(404, "Device not found")

    device = devices[0]
    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type does not match")

    modules = await FRTUModules.select(id=module_uuid)
    if not modules:
        raise HTTPException(404, "Module not found")

    module = modules[0]

    slot = await FRTUSlots.select(
        id=module.slot_id,
        device_id=device_uuid,
    )
    if not slot:
        raise HTTPException(403, "Module does not belong to this device")

    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.strip().upper() != "DO":
        raise HTTPException(
            status_code=400,
            detail="This API supports only DO modules. Use appropriate endpoint for other module types."
        )

    slot = slot[0]

    attribute = module.attribute or {}
    channel_blob = module.channel or {}

    module_info = attribute.get("module_do_info", {})
    general_info = module_info.get("general_info", {})

    channels_dict = channel_blob.get("channels") or {}

    channels_list = []
    sp_count = 0
    dp_count = 0
    visited_pairs = set()

    for ch in channels_dict.values():
        ch_copy = dict(ch)

        if "associateChannelNo" in ch_copy:
            ch_copy["associateChannelNo"] = ch_copy.pop("associateChannelNo")

        if "channel_id" in ch_copy:
            ch_copy["channelId"] = ch_copy.pop("channel_id")

        ch_type = ch_copy.get("channelType")
        if ch_type == "Single Point Parameter":
            sp_count += 1
        elif ch_type == "Double Point Parameter":
            assoc = ch_copy.get("associateChannelNo")
            if assoc:
                pair_key = tuple(sorted([ch_copy["channelNo"], assoc]))
                if pair_key not in visited_pairs:
                    dp_count += 1
                    visited_pairs.add(pair_key)

        channels_list.append(ch_copy)

    channels_list.sort(key=lambda x: int(x["channelNo"]))

    return {
        "status": "success",
        "http_code": 200,
        "message": "DO module fetched successfully",
        "sub_module_id": str(module.id),
        "device_id": str(device_uuid),
        "slot_id": str(slot.id),
        "slot_number": int(slot.name),
        "module_type": "DO",
        "general_info": general_info,
        "channels": channels_list,
        "sp_channels_count": sp_count,
        "dp_channels_count": dp_count,
    }

async def edit_do_module_info(
    device_id: str,
    device_type: str,
    payload: dict,
    user_id: UUID,
):
    try:
        device_uuid = UUID(device_id)
        sub_module_id = UUID(payload["sub_module_id"])
        new_slot_id = UUID(payload["slot_id"])
    except Exception:
        raise HTTPException(400, "Invalid UUID format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(404, "Device not found")
    device = devices[0]

    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=sub_module_id)
    if not modules:
        raise HTTPException(404, "Invalid sub_module_id")
    module = modules[0]

    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "DO":
        raise HTTPException(400, "Only DO modules supported")

    old_slot_id = module.slot_id
    old_slot_row = (await FRTUSlots.select(id=old_slot_id))[0]
    old_slot_number = int(old_slot_row.name)

    new_slot_rows = await FRTUSlots.select(id=new_slot_id, device_id=device_uuid)
    if not new_slot_rows:
        raise HTTPException(400, "Target slot does not belong to device")
    new_slot_number = int(new_slot_rows[0].name)

    moved = old_slot_id != new_slot_id

    if moved:
        occupied = await FRTUModules.select(slot_id=new_slot_id)
        if occupied:
            raise HTTPException(
                400,
                f"Slot {new_slot_number} already occupied by another module"
            )

    attribute = dict(module.attribute or {})
    channel_blob = dict(module.channel or {"channels": {}})

    module_info = attribute.get("module_do_info", {})
    general_info = dict(module_info.get("general_info", {}))

    if payload.get("general_info"):
        general_info.update(payload["general_info"])

    general_info.update({
        "slotNumber": new_slot_number,
        "slot_id": str(new_slot_id),
    })

    module_info["general_info"] = general_info
    attribute["module_do_info"] = module_info
    module_display_name = general_info.get("name")
    await validate_unique_module_name(
        device_id=device_uuid,
        module_type_name="DO",
        module_name=module_display_name,
        current_module_id=sub_module_id,
    )

    existing_channels = channel_blob.get("channels", {})

    for ch in payload.get("channels", []):
        norm = normalize_do_channel(ch)
        key = f"channel_{norm['channelNo']}"

        existing = existing_channels.get(key, {})
        norm["channelId"] = existing.get("channelId") or str(uuid4())

        existing_channels[key] = {
            **existing,
            **norm,
        }

    normalize_do_dp_associations(existing_channels)
    enforce_do_rules(existing_channels)

    channel_blob["channels"] = existing_channels

    await FRTUModules.update(
        conditions={"id": sub_module_id},
        slot_id=new_slot_id,
        attribute=attribute,
        channel=channel_blob,
    )

    if moved:
        await asyncio.to_thread(
            frtu_client.remove_devids_slot,
            old_slot_number,
        )

    await asyncio.to_thread(
        frtu_client.update_devids_conf,
        new_slot_number,
        "DO",
    )

    await asyncio.to_thread(
        update_do_ini_for_module,
        device_id,
        new_slot_number,
        existing_channels,
    )

    if moved:
        await asyncio.to_thread(
            clear_do_ini_slot,
            device_id,
            old_slot_number,
        )

    return {
        "status": "success",
        "http_code": 200,
        "message": "DO module moved and updated successfully",
        "sub_module_id": str(sub_module_id),
        "old_slot_number": old_slot_number,
        "new_slot_number": new_slot_number,
        "updated_general_info": bool(payload.get("general_info")),
        "updated_channels_count": len(payload.get("channels", [])),
        "total_channels": len(existing_channels),
    }

# async def delete_do_module(device_id: str, device_type: str, sub_module_id: str):
#     device_uuid = UUID(device_id)
#     module_uuid = UUID(sub_module_id)

#     device = (await FRTUDevices.select(id=device_uuid))[0]
#     db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
#     if db_type.upper() != device_type.upper():
#         raise HTTPException(400, "Device type mismatch")

#     module = (await FRTUModules.select(id=module_uuid))[0]
#     slot = (await FRTUSlots.select(id=module.slot_id, device_id=device_uuid))[0]
#     slot_number = int(slot.name)

#     module_type = (await FRTUModuleType.select(id=module.module_type))[0].name.upper()
#     if module_type != "DO":
#         raise HTTPException(400, "Only DO modules can be deleted from this API")

#     attribute = module.attribute or {}
#     serial_number = attribute.get("module_do_info", {}).get("general_info", {}).get("serial_number")

#     if serial_number:
#         await asyncio.to_thread(clear_do_ini_slot, serial_number, slot_number)

#     await asyncio.to_thread(frtu_client.remove_devids_slot, slot_number)

#     await FRTUModules.delete(conditions={"id": module_uuid})

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "DO module deleted successfully",
#         "data": {"slot_number": slot_number},
#     }

async def delete_do_module(device_id: str, device_type: str, sub_module_id: str, user_id: UUID):
    device_uuid = UUID(device_id)
    module_uuid = UUID(sub_module_id)

    module = (await FRTUModules.select(id=module_uuid))[0]

    slot = (await FRTUSlots.select(id=module.slot_id))[0]
    slot_number = int(slot.name)

    await FRTUModules.delete(conditions={"id": module_uuid})

    await asyncio.to_thread(frtu_client.delete_do_module, slot_number)

    return {
        "status": "success",
        "message": f"DO Module at slot {slot_number} deleted successfully"
    }

