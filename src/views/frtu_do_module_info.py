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
from src.validators.do_channel_validator import enforce_do_rules, normalize_do_channel, normalize_do_dp_associations, normalize_do_dp_associations, validate_do_channels


# async def add_do_module_info(
#     device_id: str,
#     device_type: str,
#     payload: DOModulePayload,
#     user_id: UUID,
#     ):
#     device_uuid = UUID(device_id)
#     device = (await FRTUDevices.select(id=device_uuid))[0]

#     db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
#     if db_type.upper() != device_type.upper():
#         raise HTTPException(400, "Device type mismatch")

#     slot = (await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid))[0]
#     slotNumber = int(slot.name)

#     mtype = (await FRTUModuleType.select(name="DO"))[0]

#     existing_modules = await FRTUModules.select(slot_id=payload.slot_id)
#     existing_module = existing_modules[0] if existing_modules else None

#     attribute = {}
#     channels_blob = {"channels": {}}

#     if existing_module:
#         attribute = dict(existing_module.attribute or {})
#         channels_blob = dict(existing_module.channel or {"channels": {}})

#     if payload.general_info:
#         attribute["module_do_info"] = {
#             "general_info": {
#                 **payload.general_info,
#                 "slotNumber": slotNumber,
#                 "slot_id": str(payload.slot_id),
#                 # "module_name": "Digital Output",
#                 # "module_type": "DO",
#             }
#         }

#     if payload.channels:
#         if "module_do_info" not in attribute:
#             raise HTTPException(400, "Configure general_info before adding channels")

#         for ch in payload.channels:
#             norm = normalize_do_channel(ch)
#             key = f"channel_{norm['channelNo']}"

#             existing = channels_blob["channels"].get(key, {})
#             norm["channelId"] = existing.get("channelId") or str(uuid4())

#             channels_blob["channels"][key] = {
#                 **existing,
#                 **norm,
#             }
#         normalize_do_dp_associations(channels_blob["channels"])
#         enforce_do_rules(channels_blob["channels"])

#     if existing_module:
#         module_id = existing_module.id
#         await FRTUModules.update(
#             conditions={"id": existing_module.id},
#             attribute=attribute,
#             channel=channels_blob,
#         )
#     else:
#         obj = await FRTUModules.insert(
#             slot_id=payload.slot_id,
#             name="Digital Output",
#             module_type=mtype.id,
#             attribute=attribute,
#             channel=channels_blob,
#         )
#         module_id = str(obj.id)

#     await asyncio.to_thread(
#         frtu_client.update_devids_conf,
#         slotNumber,
#         "DO",
#     )
#     await asyncio.to_thread(
#         update_do_ini_for_module,
#         device_id,
#         slotNumber,
#         channels_blob["channels"],
#     )

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "DO module configured successfully",
#         "module_id": str(module_id),
#     }

async def add_do_module_info(
    device_id: str,
    device_type: str,
    payload: DOModulePayload,
    user_id: UUID,
):
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

    do_type = (await FRTUModuleType.select(name="DO"))[0]

    existing_modules = await FRTUModules.select(slot_id=payload.slot_id)
    existing_module = existing_modules[0] if existing_modules else None

    attribute = {}
    channel_blob = {"channels": {}}

    if existing_module:
        attribute = dict(existing_module.attribute or {})
        channel_blob = dict(existing_module.channel or {"channels": {}})

    module_info = attribute.get("module_do_info", {})
    general_info = dict(module_info.get("general_info", {}))

    if payload.general_info:
        general_info.update(payload.general_info)

    general_info.update({
        "slotNumber": slot_number,
        "slot_id": str(payload.slot_id),
        "module_type": "DO",
        "module_name": "Digital Output",
    })

    attribute["module_do_info"] = {
        "general_info": general_info
    }

    channels = channel_blob.get("channels", {})

    if payload.channels:
        for ch in payload.channels:
            norm = normalize_do_channel(ch)

            ch_no = str(norm["channelNo"])
            key = f"channel_{ch_no}"

            existing = channels.get(key, {})

            norm["channelId"] = (
                ch.channelId
                if hasattr(ch, "channelId") and ch.channelId
                else existing.get("channelId")
                or str(uuid4())
            )

            channels[key] = {
                **existing,
                **norm,
                "channelNo": ch_no,
            }

        normalize_do_dp_associations(channels)
        enforce_do_rules(channels)

    channel_blob["channels"] = channels

    if existing_module:
        await FRTUModules.update(
            conditions={"id": existing_module.id},
            attribute=attribute,
            channel=channel_blob,
        )
        module_id = existing_module.id
    else:
        obj = await FRTUModules.insert(
            slot_id=payload.slot_id,
            name="Digital Output",
            module_type=do_type.id,
            attribute=attribute,
            channel=channel_blob,
        )
        module_id = obj.id

    await asyncio.to_thread(
        frtu_client.update_devids_conf,
        slot_number,
        "DO",
    )

    await asyncio.to_thread(
        update_do_ini_for_module,
        device_id,
        slot_number,
        channels,
    )

    return {
        "status": "success",
        "http_code": 200,
        "message": "DO module configured successfully",
        "data": {
            "module_id": str(module_id),
            "slot_number": slot_number,
            "configured_channels": len(channels),
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


# async def edit_do_module_info(
#     device_id: str,
#     device_type: str,
#     payload: dict,
#     user_id: UUID,
#     ):
#     try:
#         device_uuid = UUID(device_id)
#         sub_module_id = UUID(payload["sub_module_id"])
#         new_slot_id = UUID(payload["slot_id"])
#     except Exception:
#         raise HTTPException(400, "Invalid UUID format")

#     device = (await FRTUDevices.select(id=device_uuid))[0]
#     db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
#     if db_type.upper() != device_type.upper():
#         raise HTTPException(400, "Device type mismatch")

#     modules = await FRTUModules.select(id=sub_module_id)
#     if not modules:
#         raise HTTPException(404, "Invalid sub_module_id")
#     module = modules[0]

#     module_type = (await FRTUModuleType.select(id=module.module_type))[0]
#     if module_type.name.upper() != "DO":
#         raise HTTPException(400, "Only DO modules supported")

#     old_slot_id = module.slot_id

#     new_slot = await FRTUSlots.select(id=new_slot_id, device_id=device_uuid)
#     if not new_slot:
#         raise HTTPException(400, "Target slot not part of device")

#     if old_slot_id != new_slot_id:
#         occupied = await FRTUModules.select(slot_id=new_slot_id)
#         if occupied:
#             raise HTTPException(400, "Target slot is not empty")

#     old_slot_number = int((await FRTUSlots.select(id=old_slot_id))[0].name)
#     new_slot_number = int(new_slot[0].name)

#     attribute = dict(module.attribute or {})
#     channel_blob = dict(module.channel or {"channels": {}})

#     module_info = attribute.get("module_do_info", {})
#     general_info = dict(module_info.get("general_info", {}))

#     if "general_info" in payload:
#         general_info.update(payload["general_info"])

#     general_info["slotNumber"] = new_slot_number
#     general_info["slot_id"] = str(new_slot_id)

#     module_info["general_info"] = general_info
#     attribute["module_do_info"] = module_info

#     existing_channels = channel_blob.get("channels", {})

#     for ch in payload.get("channels", []):
#         norm = normalize_do_channel(ch)
#         key = f"channel_{norm['channelNo']}"

#         existing = existing_channels.get(key, {})
#         norm["channelId"] = existing.get("channelId") or str(uuid4())

#         existing_channels[key] = {
#             **existing,
#             **norm,
#         }

#     normalize_do_dp_associations(existing_channels)
#     enforce_do_rules(existing_channels)

#     channel_blob["channels"] = existing_channels

#     await FRTUModules.update(
#         conditions={"id": sub_module_id},
#         slot_id=new_slot_id,
#         attribute=attribute,
#         channel=channel_blob,
#     )

#     await asyncio.to_thread(
#         frtu_client.update_devids_conf,
#         new_slot_number,
#         "DO",
#     )

#     if old_slot_id != new_slot_id:
#         await asyncio.to_thread(
#             frtu_client.update_devids_conf,
#             old_slot_number,
#             "EMPTY",
#         )

#     await asyncio.to_thread(
#         update_do_ini_for_module,
#         device_id,
#         new_slot_number,
#         existing_channels,
#     )

#     if old_slot_id != new_slot_id:
#         await asyncio.to_thread(
#             clear_do_ini_slot,
#             device_id,
#             old_slot_number,
#         )

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "DO module updated successfully",
#         "sub_module_id": str(sub_module_id),
#         "slot_id": str(new_slot_id),
#         "slot_number": new_slot_number,
#         "total_channels": len(existing_channels),
#     }

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

