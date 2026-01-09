import asyncio
from copy import deepcopy
from typing import Any, Dict, List
from uuid import UUID, uuid4
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.utils.config_parser import update_devids_conf
from src.utils.di_ini_builder import clear_di_ini_slot, update_di_ini_for_module
from src.utils.frtu_client import frtu_client
from src.validators.di_channel_validator import DP, SP, normalize_dp_associations, validate_di_channels, validate_di_channels_strict

# ------------------------------------------add di module general info and channels working for sp and dp------------------------------------------
async def add_di_module_info(
    device_id: str,
    device_type: str,
    payload,
    user_id: UUID,
) -> Dict[str, Any]:

    device_uuid = UUID(device_id)
    device = (await FRTUDevices.select(id=device_uuid))[0]

    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.upper() != device_type.upper():
        raise HTTPException(400, "Device type does not match")

    if payload.module_type.upper() != "DI":
        raise HTTPException(400, "Only DI modules supported")

    slot_obj = (await FRTUSlots.select(id=payload.slot_id, device_id=device_uuid))[0]
    slot = {c.name: getattr(slot_obj, c.name) for c in slot_obj.__table__.columns}
    slot_number = int(slot["name"])

    mtype = (await FRTUModuleType.select(name="DI"))[0]

    existing_modules = await FRTUModules.select(slot_id=payload.slot_id)

    # NEW: protect slot from non‑DI module
    if existing_modules:
        existing_module = existing_modules[0]
        # If existing module_type is not DI, block configuration
        if getattr(existing_module, "module_type", None) and existing_module.module_type != mtype.id:
            raise HTTPException(
                400,
                "This slot is already occupied by another module type and cannot be configured as DI",
            )

    info_key = "module_di_info"
    general_info: Dict[str, Any] = {}
    channel_blob: Dict[str, Any] = {"channels": {}}
    existing_module_id = None

    if existing_modules:
        m = existing_modules[0]
        existing_module_id = str(m.id)
        if m.attribute:
            general_info = dict(m.attribute.get(info_key, {}).get("general_info", {}))
        if m.channel:
            channel_blob = dict(m.channel)

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

        temp_channels[key] = {
            **ch.dict(exclude={"associateChannelNo"}),
            "channel_no": ch_no,
            "associate_channel_no": ch.associateChannelNo,
            "channel_id": temp_channels.get(key, {}).get("channel_id") or str(uuid4()),
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
            module_type=mtype.id,
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
            module_type=mtype.id,
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

async def edit_di_module_info(
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

    device = (await FRTUDevices.select(id=device_uuid))[0]
    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=sub_module_id)
    if not modules:
        raise HTTPException(404, "Invalid sub_module_id or module not found")
    module = modules[0]

    module_type = (await FRTUModuleType.select(id=module.module_type))[0]
    if module_type.name.upper() != "DI":
        raise HTTPException(400, "This API supports only DI modules")

    slot_check = await FRTUSlots.select(id=module.slot_id, device_id=device_uuid)
    if not slot_check:
        raise HTTPException(403, "Module does not belong to this device")

    old_slot_id = module.slot_id

    new_slot = await FRTUSlots.select(id=new_slot_id, device_id=device_uuid)
    if not new_slot:
        raise HTTPException(400, "Target slot does not belong to this device")

    if old_slot_id != new_slot_id:
        occupied = await FRTUModules.select(slot_id=new_slot_id)
        if occupied:
            raise HTTPException(400, "Target slot is not empty")

    new_slot_number = int(new_slot[0].name)
    old_slot_number = int((await FRTUSlots.select(id=old_slot_id))[0].name)

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

    for ch in payload.get("channels", []):
        ch_no = str(int(ch["channelNoPrimary"]))
        key = f"channel_{ch_no}"
        if key not in existing_channels:
            raise HTTPException(400, f"Channel {ch_no} does not exist")
        existing_channels[key].update(
            {k: v for k, v in ch.items() if k != "channelNoPrimary"}
        )

    normalize_dp_associations(existing_channels)
    validate_di_channels(existing_channels)
    validate_di_channels_strict(existing_channels)

    channel_blob["channels"] = existing_channels

    await FRTUModules.update(
        conditions={"id": sub_module_id},
        slot_id=new_slot_id,
        attribute=attribute,
        channel=channel_blob,
    )

    await asyncio.to_thread(
        frtu_client.update_devids_conf,
        new_slot_number,
        "DI",
    )

    if old_slot_id != new_slot_id:
        await asyncio.to_thread(
            frtu_client.update_devids_conf,
            old_slot_number,
            "EMPTY",
        )

    await asyncio.to_thread(
        update_di_ini_for_module,
        device_id,
        new_slot_number,
        existing_channels,
    )

    if old_slot_id != new_slot_id:
        await asyncio.to_thread(
            clear_di_ini_slot,
            device_id,
            old_slot_number,
        )

    return {
        "status": "success",
        "http_code": 200,
        "message": "DI module moved successfully",
        "sub_module_id": str(sub_module_id),
        "new_slot_id": str(new_slot_id),
        "new_slot_number": new_slot_number,
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
    if db_type.upper() != device_type.upper():
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
    if module_type.name.upper() != "DI":
        raise HTTPException(400, "This API supports only DI modules")

    slot = slot[0]

    attribute = module.attribute or {}
    channel_blob = module.channel or {}

    module_info = attribute.get("module_di_info", {})
    general_info = module_info.get("general_info", {})

    channels_dict = channel_blob.get("channels") or {}

    channels_list = []
    sp_count = 0
    dp_count = 0

    for ch in channels_dict.values():
        ch_copy = dict(ch)

        if "associate_channel_no" in ch_copy:
            ch_copy["associateChannelNo"] = ch_copy.pop("associate_channel_no")

        if "channel_id" in ch_copy:
            ch_copy["channelId"] = ch_copy.pop("channel_id")

        if ch_copy.get("channelType") == "Single Point Parameter":
            sp_count += 1
        elif ch_copy.get("channelType") == "Double Point Parameter":
            dp_count += 1

        channels_list.append(ch_copy)

    channels_list.sort(key=lambda x: int(x["channel_no"]))

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
