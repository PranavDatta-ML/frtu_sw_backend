import asyncio
from typing import Any, Dict
from uuid import UUID
import logging
from fastapi import HTTPException
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.utils.frtu_client import frtu_client
from src.utils.di_ini_builder import update_di_ini_for_module
from src.utils.do_ini_builder import clear_do_ini_slot, update_do_ini_for_module
from src.validators.di_channel_validator import normalize_dp_associations, validate_di_channels, validate_di_channels_strict
from src.validators.do_channel_validator import enforce_do_rules, normalize_do_dp_associations


async def delete_channel(device_id, device_type, sub_module_id, channel_id, user_id, expected_module_type):
    device_uuid = UUID(device_id)
    module_uuid = UUID(sub_module_id)

    device = (await FRTUDevices.select(id=device_uuid))[0]

    db_type = device.type.name if hasattr(device.type, "name") else str(device.type)
    if db_type.upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    module = (await FRTUModules.select(id=module_uuid))[0]
    slot = (await FRTUSlots.select(id=module.slot_id))[0]
    slot_number = int(slot.name)

    module_type_row = (await FRTUModuleType.select(id=module.module_type))[0]
    module_type = module_type_row.name.upper()

    # 🔒 CRITICAL CHECK
    if module_type != expected_module_type:
        raise HTTPException(
            400,
            f"This API only deletes {expected_module_type} channels. Module is {module_type}."
        )

    channels = dict(module.channel.get("channels", {}))

    found_key = None
    deleted_channel = None

    for key, ch in channels.items():
        if ch.get("channelId") == channel_id:
            found_key = key
            deleted_channel = ch
            break

    if not found_key:
        raise HTTPException(404, "Channel not found")

    deleted_channel_no = deleted_channel["channelNo"]
    del channels[found_key]

    if deleted_channel.get("channelType") == "Double Point Parameter":
        assoc = deleted_channel.get("associateChannelNo")
        if assoc:
            peer_key = f"channel_{assoc}"
            if peer_key in channels:
                channels[peer_key]["associateChannelNo"] = ""

    if module_type == "DI":
        validate_di_channels(channels)
        validate_di_channels_strict(channels)
        normalize_dp_associations(channels)
        await asyncio.to_thread(update_di_ini_for_module, device_id, slot_number, channels)

    else:
        normalize_do_dp_associations(channels)
        enforce_do_rules(channels)
        await asyncio.to_thread(update_do_ini_for_module, device_id, slot_number, channels)

    await FRTUModules.update(
        conditions={"id": module_uuid},
        channel={"channels": channels},
    )

    await asyncio.to_thread(frtu_client.update_devids_conf, slot_number, module_type)

    return {
        "status": "success",
        "http_code": 200,
        "message": f"{module_type} Channel {deleted_channel_no} deleted successfully",
        "remaining_channels": len(channels),
    }

async def delete_di_channel(
    device_id: str,
    device_type: str, 
    sub_module_id: str,
    channel_id: str,
    user_id: UUID
) -> Dict[str, Any]:
    device_uuid = UUID(device_id)
    module_uuid = UUID(sub_module_id)

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(404, "Device not found")
    device = devices[0]
    
    if (device.type.name if hasattr(device.type, "name") else str(device.type)).upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=module_uuid)
    if not modules:
        raise HTTPException(404, "DI Module not found")
    module = modules[0]
    
    slots = await FRTUSlots.select(id=module.slot_id)
    if not slots:
        raise HTTPException(404, "Slot not found")
    slot = slots[0]
    slot_number = int(slot.name)

    module_types = await FRTUModuleType.select(id=module.module_type)
    if not module_types or module_types[0].name.upper() != "DI":
        raise HTTPException(400, "This API only deletes DI channels")

    channels = dict(module.channel.get("channels", {}) if module.channel else {})
    found_key = None
    deleted_channel = None
    
    for key, ch in channels.items():
        if ch.get("channelId") == channel_id:
            found_key = key
            deleted_channel = ch.copy()
            break

    if not found_key:
        raise HTTPException(404, f"DI Channel {channel_id} not found")

    deleted_channel_no = deleted_channel["channelNo"]
    del channels[found_key]

    if deleted_channel.get("channelType") == "Double Point Parameter":
        assoc = deleted_channel.get("associateChannelNo")
        if assoc:
            peer_key = f"channel_{assoc}"
            if peer_key in channels:
                channels[peer_key]["associateChannelNo"] = ""

    if channels:
        validate_di_channels(channels)
        validate_di_channels_strict(channels)
        normalize_dp_associations(channels)

    await asyncio.to_thread(update_di_ini_for_module, device_id, slot_number, channels)

    await FRTUModules.update(
        conditions={"id": module_uuid},
        channel={"channels": channels},
    )

    await asyncio.to_thread(frtu_client.update_devids_conf, slot_number, "DI")

    # log.info(f"DI Channel {deleted_channel_no} deleted from slot {slot_number}, remaining: {len(channels)}")
    
    return {
        "status": "success",
        "http_code": 200,
        "message": f"DI Channel {deleted_channel_no} deleted successfully",
        "data": {
            "slot_number": slot_number,
            "deleted_channel_no": deleted_channel_no,
            "remaining_channels": len(channels),
        },
    }

async def delete_do_channel(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    channel_id: str,
    user_id: UUID
) -> Dict[str, Any]:
    device_uuid = UUID(device_id)
    module_uuid = UUID(sub_module_id)

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(404, "Device not found")
    device = devices[0]
    
    if (device.type.name if hasattr(device.type, "name") else str(device.type)).upper() != device_type.upper():
        raise HTTPException(400, "Device type mismatch")

    modules = await FRTUModules.select(id=module_uuid)
    if not modules:
        raise HTTPException(404, "DO Module not found")
    module = modules[0]
    
    slots = await FRTUSlots.select(id=module.slot_id)
    if not slots:
        raise HTTPException(404, "Slot not found")
    slot = slots[0]
    slot_number = int(slot.name)

    module_types = await FRTUModuleType.select(id=module.module_type)
    if not module_types or module_types[0].name.upper() != "DO":
        raise HTTPException(400, "This API only deletes DO channels")

    channels = dict(module.channel.get("channels", {}) if module.channel else {})
    found_key = None
    deleted_channel = None
    
    for key, ch in channels.items():
        if ch.get("channelId") == channel_id:
            found_key = key
            deleted_channel = ch.copy()
            break

    if not found_key:
        raise HTTPException(404, f"DO Channel {channel_id} not found")

    deleted_channel_no = deleted_channel["channelNo"]
    del channels[found_key]

    if deleted_channel.get("channelType") == "Double Point Parameter":
        assoc = deleted_channel.get("associateChannelNo")
        if assoc:
            peer_key = f"channel_{assoc}"
            if peer_key in channels:
                channels[peer_key]["associateChannelNo"] = ""

    # log.info(f"Clearing do.ini slot {slot_number} (MODULE_{slot_number-3})")
    await asyncio.to_thread(clear_do_ini_slot, device_id, slot_number)

    if channels:
        normalize_do_dp_associations(channels)
        enforce_do_rules(channels)
        await asyncio.to_thread(update_do_ini_for_module, device_id, slot_number, channels)
        # log.info(f"Rewrote {len(channels)} remaining DO channels to slot {slot_number}")
    else:
        logging.log.info(f"All DO channels deleted from slot {slot_number}")

    await FRTUModules.update(
        conditions={"id": module_uuid},
        channel={"channels": channels},
    )

    await asyncio.to_thread(frtu_client.update_devids_conf, slot_number, "DO")

    logging.log.info(f"DO Channel {deleted_channel_no} deleted from slot {slot_number}, remaining: {len(channels)}")
    
    return {
        "status": "success",
        "http_code": 200,
        "message": f"DO Channel {deleted_channel_no} deleted successfully",
        "data": {
            "slot_number": slot_number,
            "deleted_channel_no": deleted_channel_no,
            "remaining_channels": len(channels),
        },
    }