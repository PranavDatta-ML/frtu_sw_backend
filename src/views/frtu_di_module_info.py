import asyncio
from copy import deepcopy
from typing import Any, Dict, List
from uuid import UUID, uuid4
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_di_module_info import ConfigureDIModuleRequest
from src.utils.config_parser import update_devids_conf
from src.utils.di_ini_builder import clear_di_ini_slot, update_di_ini_for_module, build_di_ini_payload
from src.utils.frtu_client import frtu_client
from src.validators.di_channel_validator import DP, SP, normalize_dp_associations, validate_di_channels, validate_di_channels_strict
from src.validators.di_do_name_validator import validate_unique_module_name

# ------------------------------------------add di module general info and channels working for sp and dp------------------------------------------
async def add_di_module_info(
    device_id: str,
    device_type: str,
    payload: ConfigureDIModuleRequest,
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

    if payload.module_type.upper() != "DI":
        raise HTTPException(400, "Only DI modules supported")

    slots = await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(400, "Invalid slot_id")
    slot = slots[0]

    slot_number = int(slot.name)
    if slot_number < 4:
        raise HTTPException(400, "DI allowed only from slot 4 onwards")

    di_types = await FRTUModuleType.select(name="DI")
    if not di_types:
        raise HTTPException(500, "DI module type not configured")
    di_type_id = di_types[0].id

    existing_modules = await FRTUModules.select(slot_id=payload.slot_id)

    info_key = "module_di_info"
    general_info: Dict[str, Any] = {}
    channel_blob: Dict[str, Any] = {"channels": {}}
    module_id = None

    if existing_modules:
        module = existing_modules[0]
        if module.module_type != di_type_id:
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
        "module_name": "Digital Input",
        "module_type": "DI",
    })
    module_display_name = general_info.get("name")
    await validate_unique_module_name(
        device_id=device_uuid,
        module_type_name="DI",
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

    validate_di_channels(updated_channels)
    validate_di_channels_strict(updated_channels)
    normalize_dp_associations(updated_channels)

    channel_blob["channels"] = updated_channels

    attribute = {
        "device_id": str(device_uuid),
        "slot_number": slot_number,
        info_key: {"general_info": general_info},
    }

    if module_id:
        await FRTUModules.update(
            conditions={"id": module_id},
            name="Digital Input",
            module_type=di_type_id,
            attribute=attribute,
            channel=channel_blob,
        )
        message = "DI module updated successfully"
    else:
        module = await FRTUModules.insert(
            slot_id=payload.slot_id,
            name="Digital Input",
            module_type=di_type_id,
            attribute=attribute,
            channel=channel_blob,
        )
        module_id = module.id
        message = "DI module created successfully"

    await asyncio.to_thread(
        frtu_client.update_devids_conf,
        slot_number,
        "DI",
    )

    serial_number = general_info.get("serial_number")
    if serial_number:
        await asyncio.to_thread(
            update_di_ini_for_module,
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


async def edit_di_module_info(
    device_id: str,
    device_type: str,
    payload: dict,
    user_id: UUID,
):

    device_uuid = UUID(device_id)
    sub_module_id = UUID(payload["sub_module_id"])
    new_slot_id = UUID(payload["slot_id"])

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(404, "Device not found")
    device = devices[0]

    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=sub_module_id)
    if not modules:
        raise HTTPException(404, "DI module not found")
    module = modules[0]

    module_type = await FRTUModuleType.select(id=module.module_type)
    if not module_type or module_type[0].name.upper() != "DI":
        raise HTTPException(400, "Not a DI module")

    old_slot = await FRTUSlots.select(id=module.slot_id, device_id=device_uuid)
    if not old_slot:
        raise HTTPException(403, "Module does not belong to this device")
    old_slot_number = int(old_slot[0].name)

    new_slot = await FRTUSlots.select(id=new_slot_id, device_id=device_uuid)
    if not new_slot:
        raise HTTPException(400, "Target slot invalid")
    new_slot_number = int(new_slot[0].name)

    if old_slot_number != new_slot_number:
        occupied = await FRTUModules.select(slot_id=new_slot_id)
        if occupied:
            raise HTTPException(400, "Target slot occupied")

    attribute = dict(module.attribute or {})
    channel_blob = dict(module.channel or {"channels": {}})

    general_info = attribute.get("module_di_info", {}).get("general_info", {})
    if "general_info" in payload:
        general_info.update(payload["general_info"])

    general_info["slot_number"] = new_slot_number
    general_info["slot_id"] = str(new_slot_id)

    attribute["module_di_info"] = {"general_info": general_info}
    module_display_name = general_info.get("name")
    await validate_unique_module_name(
        device_id=device_uuid,
        module_type_name="DI",
        module_name=module_display_name,
        current_module_id=sub_module_id,
    )

    channels = channel_blob.get("channels", {})
    for ch in payload.get("channels", []):
        key = f"channel_{int(ch['channelNoPrimary'])}"
        # channels.setdefault(key, {}).update(ch)
        channels.setdefault(key, {})
        channels[key]["channelNo"] = ch['channelNoPrimary']      # ← ADD THIS
        channels[key]["channelNoPrimary"] = ch['channelNoPrimary']
        channels[key].update(ch)

    validate_di_channels(channels)
    validate_di_channels_strict(channels)
    normalize_dp_associations(channels)

    channel_blob["channels"] = channels

    await FRTUModules.update(
        conditions={"id": sub_module_id},
        slot_id=new_slot_id,
        attribute=attribute,
        channel=channel_blob,
    )
    # if moved:
#         await asyncio.to_thread(
#             frtu_client.remove_devids_slot,
#             old_slot_number
#         )
#     await asyncio.to_thread(frtu_client.update_devids_conf, new_slot_number, "DI")  
#     serial_number = general_info.get("serial_number")
#     if serial_number:
#         await asyncio.to_thread(update_di_ini_for_module, serial_number, new_slot_number, existing_channels)

#         if moved:
#             await asyncio.to_thread(clear_di_ini_slot, serial_number, old_slot_number)
    if old_slot_number != new_slot_number:
        await asyncio.to_thread(frtu_client.remove_devids_slot, old_slot_number)

    await asyncio.to_thread(frtu_client.update_devids_conf, new_slot_number, "DI")

    serial_number = general_info.get("serial_number")
    if serial_number:
        await asyncio.to_thread(update_di_ini_for_module, serial_number, new_slot_number, channels)
        if old_slot_number != new_slot_number:
            await asyncio.to_thread(clear_di_ini_slot, serial_number, old_slot_number)

    return {
        "status": "success",
        "http_code": 200,
        "data": {
            "module_id": str(sub_module_id),
            "old_slot": old_slot_number,
            "new_slot": new_slot_number,
        },
    }

# ------------------------------------------get di module info by sub_module_id ------------------------------------------
async def get_di_module_info(
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
    if module_type.name.strip().upper() != "DI":
        raise HTTPException(
            status_code=400,
            detail="This API supports only DI modules. Use appropriate endpoint for other module types."
        )

    slot = slot[0]

    attribute = module.attribute or {}
    channel_blob = module.channel or {}

    module_info = attribute.get("module_di_info", {})
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

        if "channelNo" not in ch_copy and "channelNoPrimary" in ch_copy:
            ch_copy["channelNo"] = ch_copy["channelNoPrimary"]

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
        "message": "DI module fetched successfully",
        "sub_module_id": str(module.id),
        "device_id": str(device_uuid),
        "slot_id": str(slot.id),
        "slot_number": int(slot.name),
        "module_type": "DI",
        "general_info": general_info,
        "channels": channels_list,
        "sp_channels_count": sp_count,
        "dp_channels_count": dp_count,
    }


# ------------------------------------------get di module general info by slot_id ------------------------------------------
async def get_di_module_info_by_slot_id(
    device_id: str,
    device_type: str,
    slot_id: str,
    user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    device = devices[0]
    db_type = (
        device.type.name
        if hasattr(device.type, "name")
        else (device.type.value if hasattr(device.type, "value") else str(device.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match")

    try:
        slot_uuid = UUID(slot_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid slot_id format")

    slots = await FRTUSlots.select(id=slot_uuid, device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="slot_id does not belong to this device")

    modules = await FRTUModules.select(slot_id=slot_uuid)
    if not modules:
        return {
            "status": "success",
            "http_code": 200,
            "message": "No DI module configured for this slot",
            "data": {
                "module_id": None,
                "slot_id": slot_id,
                "module_type": "DI",
                "name": None,
                "general_info": {},
                "configured_channels_count": 0,
            },
        }

    module = modules[0]
    info_key = "module_di_info"
    general_info = {}
    
    if module.attribute and module.attribute.get(info_key):
        general_info = module.attribute[info_key].get("general_info", {})

    channels_count = 0
    if module.channel and module.channel.get("channels"):
        channels_count = len(module.channel["channels"])

    return {
        "status": "success",
        "http_code": 200,
        "message": "DI module info retrieved successfully",
        "data": {
            "module_id": str(module.id),
            "slot_id": slot_id,
            "module_type": "DI",
            "name": module.name or "Digital Input",
            "general_info": general_info,
            "configured_channels_count": channels_count,
        },
    }

# async def delete_di_module(device_id: str, device_type: str, sub_module_id: str):
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
#     if module_type != "DI":
#         raise HTTPException(400, "Only DI modules can be deleted from this API")

#     attribute = module.attribute or {}
#     serial_number = attribute.get("module_di_info", {}).get("general_info", {}).get("serial_number")

#     if serial_number:
#         await asyncio.to_thread(clear_di_ini_slot, serial_number, slot_number)

#     await asyncio.to_thread(frtu_client.remove_devids_slot, slot_number)

#     await FRTUModules.delete(conditions={"id": module_uuid})

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "DI module deleted successfully",
#         "data": {"slot_number": slot_number},
#     }

async def delete_di_module(device_id: str, device_type: str, sub_module_id: str, user_id: UUID):
    device_uuid = UUID(device_id)
    module_uuid = UUID(sub_module_id)

    module = (await FRTUModules.select(id=module_uuid))[0]

    slot = (await FRTUSlots.select(id=module.slot_id))[0]
    slot_number = int(slot.name)

    await FRTUModules.delete(conditions={"id": module_uuid})

    await asyncio.to_thread(frtu_client.delete_di_module, slot_number)

    return {
        "status": "success",
        "message": f"DI Module at slot {slot_number} deleted successfully"
    }

