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
        raise HTTPException(400, "Invalid device_id")
    device = devices[0]

    db_type = (
        device.type.name
        if hasattr(device.type, "name")
        else (device.type.value if hasattr(device.type, "value") else str(device.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type does not match")

    if payload.module_type.upper() != "DI":
        raise HTTPException(400, "Only DI modules supported")

    slots = await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(400, "Invalid slot_id or slot does not belong to this device")
    slot_obj = slots[0]
    slot_number = int(slot_obj.name)
    if slot_number < 4:
        raise HTTPException(400, "DI module is allowed only from slot 4 onwards")

    di_types = await FRTUModuleType.select(name="DI")
    if not di_types:
        raise HTTPException(500, "DI module type not configured")
    di_type_id = di_types[0].id

    existing_modules = await FRTUModules.select(slot_id=payload.slot_id)
    info_key = "module_di_info"
    general_info: Dict[str, Any] = {}
    channel_blob: Dict[str, Any] = {"channels": {}}
    existing_module_id = None

    if existing_modules:
        existing_module = existing_modules[0]
        if existing_module.module_type != di_type_id:
            raise HTTPException(
                400,
                "This slot is already occupied by another module type and cannot be configured as DI",
            )

        existing_module_id = str(existing_module.id)
        if existing_module.attribute:
            general_info = dict(
                existing_module.attribute.get(info_key, {}).get("general_info", {})
            )
        if existing_module.channel:
            channel_blob = dict(existing_module.channel)

    if payload.channels and not (payload.general_info or general_info):
        raise HTTPException(
            400,
            "Create general_info first before adding channels",
        )

    if payload.general_info:
        general_info.update(payload.general_info)

    if general_info:
        general_info.update(
            {
                "slot_number": slot_number,
                "slot_id": str(payload.slot_id),
                "module_name": "Digital Input",
                "module_type": "DI",
            }
        )

    existing_channels = channel_blob.get("channels", {})
    temp_channels: Dict[str, Dict[str, Any]] = dict(existing_channels)

    for ch in payload.channels or []:
        ch_no = str(int(ch.channelNoPrimary))
        key = f"channel_{ch_no}"

        ch_dict = ch.dict(exclude={"associateChannelNo"})
        channel_id = ch_dict.pop("channelId", None) if "channelId" in ch_dict else None
        if not channel_id:
            channel_id = temp_channels.get(key, {}).get("channelId") or str(uuid4())

        temp_channels[key] = {
            **ch_dict,
            "channelNo": ch_no,
            "associateChannelNo": ch.associateChannelNo,
            "channelId": channel_id,
        }

    if payload.channels:
        validate_di_channels(temp_channels)
        validate_di_channels_strict(temp_channels)
        normalize_dp_associations(temp_channels)

    channel_blob["channels"] = temp_channels

    attribute_blob = {
        "device_id": str(device_uuid),
        "slot_number": slot_number,
        info_key: {"general_info": general_info},
    }

    if existing_module_id:
        await FRTUModules.update(
            conditions={"id": UUID(existing_module_id)},
            name="Digital Input",
            module_type=di_type_id,
            attribute=attribute_blob,
            channel=channel_blob,
        )
        module_id_out = existing_module_id
        http_code = 200
        message = "DI module updated successfully"
    else:
        placed = await FRTUModules.insert(
            slot_id=payload.slot_id,
            name="Digital Input",
            module_type=di_type_id,
            attribute=attribute_blob,
            channel=channel_blob,
        )
        module_id_out = str(placed.id)
        http_code = 201
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
            channel_blob["channels"],
        )

    return {
        "status": "success",
        "http_code": http_code,
        "message": message,
        "data": {
            "module_id": module_id_out,
            "slot_id": str(payload.slot_id),
            "module_type": "DI",
            "name": "Digital Input",
            "general_info": general_info,
            "configured_channels_count": len(temp_channels),
        },
    }

# async def edit_di_module_info(
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
#     if db_type.strip().upper() != device_type.strip().upper():
#         raise HTTPException(400, "Device type mismatch")

#     modules = await FRTUModules.select(id=sub_module_id)
#     if not modules:
#         raise HTTPException(404, "Invalid sub_module_id or module not found")
#     module = modules[0]

#     module_type_obj = (await FRTUModuleType.select(id=module.module_type))[0]
#     if module_type_obj.name.strip().upper() != "DI":
#         raise HTTPException(400, "This API supports only DI modules")

#     slot_check = await FRTUSlots.select(id=module.slot_id, device_id=device_uuid)
#     if not slot_check:
#         raise HTTPException(403, "Module does not belong to this device")

#     old_slot_id = module.slot_id
#     new_slot = await FRTUSlots.select(id=new_slot_id, device_id=device_uuid)
#     if not new_slot:
#         raise HTTPException(400, "Target slot does not belong to this device")

#     if old_slot_id != new_slot_id:
#         occupied = await FRTUModules.select(slot_id=new_slot_id)
#         if occupied:
#             raise HTTPException(400, "Target slot is not empty")

#     new_slot_number = int(new_slot[0].name)
#     old_slot_number = int((await FRTUSlots.select(id=old_slot_id))[0].name)

#     attribute = dict(module.attribute or {})
#     channel_blob = dict(module.channel or {"channels": {}})

#     module_info = attribute.get("module_di_info", {})
#     general_info = dict(module_info.get("general_info", {}))

#     if "general_info" in payload:
#         general_info.update(payload["general_info"])

#     general_info["slot_number"] = new_slot_number
#     general_info["slot_id"] = str(new_slot_id)
#     module_info["general_info"] = general_info
#     attribute["module_di_info"] = module_info

#     existing_channels = channel_blob.get("channels", {})

#     for ch in payload.get("channels", []):
#         ch_no = str(int(ch["channelNoPrimary"]))
#         key = f"channel_{ch_no}"
#         if key not in existing_channels:
#             existing_channels[key] = {}
#         existing_channels[key].update(
#             {k: v for k, v in ch.items() if k != "channelNoPrimary"}
#         )

#     normalize_dp_associations(existing_channels)
#     validate_di_channels(existing_channels)
#     validate_di_channels_strict(existing_channels)

#     channel_blob["channels"] = existing_channels

#     await FRTUModules.update(
#         conditions={"id": sub_module_id},
#         slot_id=new_slot_id,
#         attribute=attribute,
#         channel=channel_blob,
#     )

#     serial_number = general_info.get("serial_number")
#     if serial_number:
#         await asyncio.to_thread(
#             frtu_client.update_devids_conf,
#             new_slot_number,
#             "DI",
#         )

#         await asyncio.to_thread(
#             update_di_ini_for_module,
#             serial_number,
#             new_slot_number,
#             existing_channels,
#         )

#         if old_slot_id != new_slot_id:
#             await asyncio.to_thread(
#                 frtu_client.update_devids_conf,
#                 old_slot_number,
#                 "EMPTY",
#             )
#             await asyncio.to_thread(
#                 clear_di_ini_slot,
#                 serial_number,
#                 old_slot_number,
#             )

#     return {
#         "status": "success",
#         "http_code": 200,
#         "message": "DI module moved and updated successfully",
#         "sub_module_id": str(sub_module_id),
#         "old_slot_id": str(old_slot_id),
#         "new_slot_id": str(new_slot_id),
#         "new_slot_number": new_slot_number,
#         "updated_general_info": bool(payload.get("general_info")),
#         "updated_channels_count": len(payload.get("channels", [])),
#     }

async def edit_di_module_info(
    device_id: str,
    device_type: str,
    payload: dict,
    user_id,
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
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=sub_module_id)
    if not modules:
        raise HTTPException(404, "Invalid sub_module_id or module not found")
    module = modules[0]

    module_type_obj = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type_obj.name.strip().upper() != "DI":
        raise HTTPException(400, "This API supports only DI modules")

    # Old slot must belong to this device
    old_slot_rows = await FRTUSlots.select(id=module.slot_id, device_id=device_uuid)
    if not old_slot_rows:
        raise HTTPException(403, "Module does not belong to this device")
    old_slot_row = old_slot_rows[0]
    old_slot_id = module.slot_id
    old_slot_number = int(old_slot_row.name)

    # New slot must belong to this device
    new_slot_rows = await FRTUSlots.select(id=new_slot_id, device_id=device_uuid)
    if not new_slot_rows:
        raise HTTPException(400, "Target slot does not belong to this device")
    new_slot_row = new_slot_rows[0]
    new_slot_number = int(new_slot_row.name)

    moved = (old_slot_id != new_slot_id)

    # Don’t allow move into occupied slot
    if moved:
        occupied = await FRTUModules.select(slot_id=new_slot_id)
        if occupied:
            raise HTTPException(400, "Target slot is not empty")

    attribute = dict(module.attribute or {})
    channel_blob = dict(module.channel or {"channels": {}})

    module_info = attribute.get("module_di_info", {})
    general_info = dict(module_info.get("general_info", {}))

    if "general_info" in payload:
        general_info.update(payload["general_info"])

    general_info["slot_number"] = new_slot_number
    general_info["slot_id"] = str(new_slot_id)
    module_info["general_info"] = general_info
    attribute["module_di_info"] = module_info

    existing_channels = channel_blob.get("channels", {})

    # Upsert channel updates
    for ch in payload.get("channels", []):
        ch_no = str(int(ch["channelNoPrimary"]))
        key = f"channel_{ch_no}"
        if key not in existing_channels:
            existing_channels[key] = {}
        existing_channels[key].update({k: v for k, v in ch.items() if k != "channelNoPrimary"})

    # DP status validation (both must be true) – uses your existing structure
    for key, ch in existing_channels.items():
        if ch.get("channelType") == "Double Point Parameter":
            assoc_no = ch.get("associateChannelNo") or ch.get("associate_channel_no")
            if assoc_no:
                assoc_key = f"channel_{assoc_no}"
                assoc_ch = existing_channels.get(assoc_key)
                if not assoc_ch:
                    raise HTTPException(400, f"DP channel {key} references missing associate channel {assoc_no}")
                if not ch.get("status") or not assoc_ch.get("status"):
                    raise HTTPException(400, f"Both channels in DP pair ({key}↔{assoc_no}) must have status=true")

    normalize_dp_associations(existing_channels)
    validate_di_channels(existing_channels)
    validate_di_channels_strict(existing_channels)

    channel_blob["channels"] = existing_channels

    # DB update first
    await FRTUModules.update(
        conditions={"id": sub_module_id},
        slot_id=new_slot_id,
        attribute=attribute,
        channel=channel_blob,
    )

    # --- FRTU side updates (devids.conf does NOT depend on serial_number) ---
    # Set new slot type
    await asyncio.to_thread(frtu_client.update_devids_conf, new_slot_number, "DI")  # [file:54]

    # Clear old slot type if moved
    if moved:
        await asyncio.to_thread(frtu_client.update_devids_conf, old_slot_number, "EMPTY")  # [file:54]

    # --- di.ini updates (depends on serial_number because you pass it as device_id) ---
    serial_number = general_info.get("serial_number")
    if serial_number:
        await asyncio.to_thread(update_di_ini_for_module, serial_number, new_slot_number, existing_channels)

        if moved:
            await asyncio.to_thread(clear_di_ini_slot, serial_number, old_slot_number)

    return {
        "status": "success",
        "http_code": 200,
        "message": "DI module moved and updated successfully",
        "sub_module_id": str(sub_module_id),
        "old_slot_id": str(old_slot_id),
        "new_slot_id": str(new_slot_id),
        "new_slot_number": new_slot_number,
        "updated_general_info": bool(payload.get("general_info")),
        "updated_channels_count": len(payload.get("channels", [])),
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


