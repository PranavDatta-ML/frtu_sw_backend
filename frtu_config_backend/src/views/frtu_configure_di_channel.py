import logging
import os
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, Query, Request, Header, Depends
from datetime import datetime, timezone
import uuid
from uuid import UUID, uuid4
from fastapi.responses import JSONResponse
from src.core.settings import Settings
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_di_module import ConfigureSingleDIChannelRequest
from src.services.module_channel import _ensure_di_module_state, _parse_assoc_no
from src.utils.access_token import decode_token
from src.utils.config_parser import parse_devids_conf
from src.utils.ini_handler import  regenerate_module_ini
logger = logging.getLogger(__name__)

async def add_di_channel(
    device_id: str,
    device_type: str,
    sub_module_id: UUID,
    channel_no: int,
    user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    dev = devices[0]
    db_type = (
        dev.type.name
        if hasattr(dev.type, "name")
        else (dev.type.value if hasattr(dev.type, "value") else str(dev.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    mods = await FRTUModules.select(id=sub_module_id)
    if not mods:
        raise HTTPException(status_code=400, detail="Invalid sub_module_id")
    m = mods[0]
    module_id = m.id
    slot_id = m.slot_id
    channel: Dict[str, Any] = dict(m.channel or {})

    slots = await FRTUSlots.select(id=slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="Module does not belong to this device")

    mtypes = await FRTUModuleType.select(id=m.module_type)
    if not mtypes or mtypes[0].name.strip().upper() != "DI":
        raise HTTPException(status_code=400, detail="Only DI sub-modules supported for this API")

    channels_dict: Dict[str, Any] = dict(channel.get("channels") or {})
    channel_no_int = int(channel_no)
    if not (1 <= channel_no_int <= 16):
        raise HTTPException(status_code=400, detail="channel_no must be between 1 and 16")
    
    key = f"channel_{channel_no_int}"
    if key in channels_dict:
        raise HTTPException(status_code=400, detail=f"Channel {channel_no_int} already exists")

    channel_id = str(uuid4())
    default_name = f"DI Channel {channel_no_int:02d}"

    channels_dict[key] = {
        "channel_id": channel_id,
        "channel_no": str(channel_no_int),
        "channel_name": default_name,
    }

    channel["channels"] = channels_dict

    await FRTUModules.update(
        conditions={"id": module_id},
        channel=channel,
    )
    channel_list = [
        {
            "channel_id": v.get("channel_id"),
            "channel_no": v.get("channel_no"),
            "channel_name": v.get("name", f"DI Channel {int(v.get('channel_no', 0)):02d}"),
        }
        for v in channels_dict.values()
    ]

    # channel_list: List[Dict[str, Any]] = []
    # for k, v in channels_dict.items():
    #     channel_list.append(
    #         {
    #             k: {
    #                 "channel_id": v.get("channel_id"),
    #                 "channel_no": v.get("channel_no"),
    #             }
    #         }
    #     )

    return {
        "status": "success",
        "message": "DI channel added successfully",
        "device_id": device_id,
        "sub_module_id": str(module_id),
        "channel": channel_list,
    }

async def get_di_channel_list(
    device_id: str,
    device_type: str,
    sub_module_id: UUID,
    user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    dev = devices[0]
    db_type = (
        dev.type.name
        if hasattr(dev.type, "name")
        else (dev.type.value if hasattr(dev.type, "value") else str(dev.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match")

    mods = await FRTUModules.select(id=sub_module_id)
    if not mods:
        raise HTTPException(status_code=400, detail="Invalid sub_module_id")
    m = mods[0]
    module_id = m.id

    slots = await FRTUSlots.select(id=m.slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="Module does not belong to this device")

    mtypes = await FRTUModuleType.select(id=m.module_type)
    if not mtypes or mtypes[0].name.strip().upper() != "DI":
        raise HTTPException(status_code=400, detail="Only DI modules supported")

    channel: Dict[str, Any] = dict(m.channel or {})
    channels_dict: Dict[str, Any] = dict(channel.get("channels") or {})

    channel_list = []
    for v in channels_dict.values():
        channel_no_raw = v.get("channel_no")
        if channel_no_raw is None:
            continue
            
        try:
            ch_no_int = int(str(channel_no_raw))
        except ValueError:
            ch_no_int = None

        stored_name = v.get("name")
        if stored_name:
            channel_name = stored_name
        elif ch_no_int is not None:
            channel_name = f"DI Channel {ch_no_int:02d}"
        else:
            channel_name = None

        channel_list.append({
            "channel_id": v.get("channel_id"),
            "channel_no": str(ch_no_int) if ch_no_int is not None else str(channel_no_raw),
            "channel_name": channel_name,
        })
    return {
        "status": "success",
        "message": "DI channel fetched successfully",
        "device_id": device_id,
        "sub_module_id": str(module_id),
        "channel": channel_list,
    }


# async def configure_di_channel_info_func(
#     device_id: str,
#     device_type: str,
#     payload: ConfigureSingleDIChannelRequest,
#     user_id: UUID,
# ) -> Dict[str, Any]:
#     try:
#         device_uuid = UUID(device_id)
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid device_id format")

#     devices = await FRTUDevices.select(id=device_uuid)
#     if not devices:
#         raise HTTPException(status_code=400, detail="Invalid device_id")
#     dev = devices[0]
#     db_type = (
#         dev.type.name
#         if hasattr(dev.type, "name")
#         else (dev.type.value if hasattr(dev.type, "value") else str(dev.type))
#     )
#     if db_type.strip().upper() != device_type.strip().upper():
#         raise HTTPException(status_code=400, detail="Device type does not match")

#     state = await _ensure_di_module_state(device_uuid, payload.sub_module_id)
#     module_id: UUID = state["module_id"]
#     attr: Dict[str, Any] = state["attribute"]
#     channel: Dict[str, Any] = state["channel"]
#     info_key: str = state["info_key"]

#     modules = await FRTUModules.select(id=module_id)
#     if not modules:
#         raise HTTPException(status_code=400, detail="Module not found")
#     m = modules[0]
#     slot_id = m.slot_id

#     channels_map: Dict[str, Any] = dict(channel.get("channels") or {})
    
#     req = payload.channel
#     ch_id = req.channel_id
#     channel_type = req.channel_type
#     if channel_type == "Double Point Parameter" and not req.associate_channel_id:
#         raise HTTPException(status_code=400, detail="associate_channel_id required for Double Point Parameter")
#     target_key = None
#     target_no = None
#     for key, idx in channels_map.items():
#         if idx.get("channel_id") == ch_id:
#             target_key = key
#             target_no = idx.get("channel_no")
#             break

#     if not target_key:
#         raise HTTPException(status_code=400, detail="channel_id not found")

#     for field, value in req.dict(exclude_unset=True).items():
#         channels_map[target_key][field] = value

#     used_as_assoc_ids: set[str] = set()
#     for cfg in channels_map.values():
#         assoc_id = cfg.get("associate_channel_id")
#         if assoc_id:
#             used_as_assoc_ids.add(assoc_id)

#     associateable_channels: List[Dict[str, Any]] = []
#     for key, cfg in channels_map.items():
#         cid = cfg.get("channel_id")
#         if cid == ch_id:
#             continue
#         if cfg.get("channel_type") != "Single Point Parameter":
#             continue
#         if cid in used_as_assoc_ids:
#             continue
#         if not cfg.get("is_enabled", False):
#             continue
#         associateable_channels.append({
#             "label": f"DI channel {cfg.get('channel_no')}",
#             "channel_id": cid,
#             "channel_no": cfg.get("channel_no"),
#         })

#     for k, cfg in channels_map.items():
#         if cfg.get("channel_no"):
#             try:
#                 cfg["channel_no"] = str(int(str(cfg["channel_no"])))
#             except ValueError:
#                 pass
#     target_cfg = channels_map[target_key]
#     associate_channel_id = target_cfg.get("associate_channel_id")
    
#     if target_cfg.get("channel_type") == "Double Point Parameter" and associate_channel_id:
#         assoc_id = associate_channel_id
#         assoc_entry = None
#         assoc_key = None
        
#         for key, cfg in channels_map.items():
#             if cfg.get("channel_id") == assoc_id:
#                 assoc_key = key
#                 assoc_entry = cfg
#                 break

#         if not assoc_entry:
#             raise HTTPException(status_code=400, detail=f"Associated channel {assoc_id} not found")

#         if assoc_entry.get("channel_type") not in (None, "Single Point Parameter"):
#             raise HTTPException(status_code=400, detail=f"Associated channel must be Single Point Parameter")

#         if not assoc_entry.get("is_enabled", False):
#             raise HTTPException(status_code=400, detail=f"Associated channel must be enabled")

#         main_ioa = target_cfg.get("ioa")
#         if not main_ioa:
#             raise HTTPException(status_code=400, detail="ioa required for Double Point")

#         target_cfg["ioa"] = main_ioa
#         target_cfg["channel_type"] = "Double Point Parameter"
        
#         assoc_entry["ioa"] = main_ioa
#         assoc_entry["channel_type"] = "Double Point Parameter"
#         assoc_entry["associate_channel_id"] = ch_id
        
#         channels_map[target_key] = target_cfg
#         channels_map[assoc_key] = assoc_entry

#     target_cfg = channels_map[target_key]
#     if target_cfg.get("timestamp_enable") is not None and target_cfg.get("io_activation_mode") is not None:
#         target_cfg["is_enabled"] = target_cfg["timestamp_enable"] and target_cfg["io_activation_mode"] not in ("0", "0: disabled")

#     channel["channels"] = channels_map

#     await FRTUModules.update(
#         conditions={"id": module_id},
#         attribute=attr,
#         channel=channel,
#     )

#     module_info = attr.get(info_key, {})
#     general_info = module_info.get("general_info", {})
#     slot_number = general_info.get("slot_number")
#     if not slot_number:
#         raise HTTPException(status_code=500, detail="slot_number not found")

#     module_num = int(slot_number) - 3
#     serial_channel = f"MODULE_{module_num}"

#     dp_pairs_set = set()
#     for cfg in channels_map.values():
#         if cfg.get("channel_type") != "Double Point Parameter" or not cfg.get("is_enabled"):
#             continue
            
#         assoc_id = cfg.get("associate_channel_id")
#         if not assoc_id:
#             continue
            
#         assoc_ch = next((c for c in channels_map.values() if c.get("channel_id") == assoc_id), None)
#         if not assoc_ch or assoc_ch.get("channel_type") != "Double Point Parameter":
#             continue
            
#         a = int(cfg["channel_no"])
#         b = int(assoc_ch["channel_no"])
#         if a != b:
#             p1, p2 = (a, b) if a < b else (b, a)
#             dp_pairs_set.add(f"{p1},{p2}")

#     dp_pairs = sorted(dp_pairs_set, key=lambda x: int(x.split(",")[0]))

#     regenerate_module_ini(
#         ini_path="rtu_config_iec104_di.ini",
#         serial_channel=serial_channel,
#         channels=channels_map,
#         dp_pairs=dp_pairs,
#     )

#     logger.info(f"FRTU di.ini: Slot {slot_number} → {serial_channel}, dp_pairs={dp_pairs}")

#     return {
#         "status": "success",
#         "message": "DI channel configured successfully",
#         "device_id": device_id,
#         "sub_module_id": str(module_id),
#         "channels": channels_map,
#         "associateable_channels": associateable_channels,
#     }

async def configure_di_channel_info_func(
    device_id: str,
    device_type: str,
    payload: ConfigureSingleDIChannelRequest,
    user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    dev = devices[0]
    db_type = (
        dev.type.name
        if hasattr(dev.type, "name")
        else (dev.type.value if hasattr(dev.type, "value") else str(dev.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match")

    state = await _ensure_di_module_state(device_uuid, payload.sub_module_id)
    module_id: UUID = state["module_id"]
    attr: Dict[str, Any] = state["attribute"]
    channel: Dict[str, Any] = state["channel"]
    info_key: str = state["info_key"]

    modules = await FRTUModules.select(id=module_id)
    if not modules:
        raise HTTPException(status_code=400, detail="Module not found")
    m = modules[0]
    slot_id = m.slot_id

    channels_map: Dict[str, Any] = dict(channel.get("channels") or {})
    
    req = payload.channel
    ch_id = req.channel_id
    channel_type = req.channel_type
    
    target_key = None
    target_no = None
    for key, idx in channels_map.items():
        if idx.get("channel_id") == ch_id:
            target_key = key
            target_no = idx.get("channel_no")
            break

    if not target_key:
        raise HTTPException(status_code=400, detail="channel_id not found")

    for field, value in req.dict(exclude_unset=True).items():
        channels_map[target_key][field] = value

    # Track standalone DP channels and used associations
    standalone_dp_channels = []
    used_as_assoc = set()
    for key, cfg in channels_map.items():
        assoc_id = cfg.get("associate_channel_id")
        if assoc_id:
            used_as_assoc.add(assoc_id)
        elif not assoc_id and cfg.get("channel_type") == "Double Point Parameter" and cfg.get("is_enabled", False):
            if cfg.get("channel_id") not in used_as_assoc:
                standalone_dp_channels.append({
                    "channel_id": cfg.get("channel_id"),
                    "channel_no": cfg.get("channel_no"),
                    "label": f"DI channel {cfg.get('channel_no')}",
                    "normal_state": cfg.get("normal_state", "")
                })

    associateable_channels: List[Dict[str, Any]] = standalone_dp_channels

    for k, cfg in channels_map.items():
        if cfg.get("channel_no"):
            try:
                cfg["channel_no"] = str(int(str(cfg["channel_no"])))
            except ValueError:
                pass

    target_cfg = channels_map[target_key]
    associate_channel_id = target_cfg.get("associate_channel_id")
    
    # STRICT: No changing associations - error if already associated
    if channel_type == "Double Point Parameter":
        # Check if target channel already has ANY association
        if target_cfg.get("associate_channel_id"):
            current_assoc_id = target_cfg.get("associate_channel_id")
            raise HTTPException(
                status_code=400, 
                detail=f"Target channel already associated with channel {current_assoc_id}"
            )
        
        if associate_channel_id:
            assoc_id = associate_channel_id
            assoc_entry = None
            assoc_key = None
            
            for key, cfg in channels_map.items():
                if cfg.get("channel_id") == assoc_id:
                    assoc_key = key
                    assoc_entry = cfg
                    break
            
            if not assoc_entry:
                raise HTTPException(status_code=400, detail=f"Associated channel {assoc_id} not found")
            
            # Check if assoc channel already has ANY association
            if assoc_entry.get("associate_channel_id"):
                current_assoc_id = assoc_entry.get("associate_channel_id")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Associated channel already paired with channel {current_assoc_id}"
                )
            
            if assoc_entry.get("channel_type") != "Double Point Parameter":
                raise HTTPException(status_code=400, detail="Associated channel must be Double Point Parameter")
            if not assoc_entry.get("is_enabled", False):
                raise HTTPException(status_code=400, detail="Associated channel must be enabled")
            
            main_normal_state = target_cfg.get("normal_state", "").upper()
            assoc_normal_state = assoc_entry.get("normal_state", "").upper()
            
            if main_normal_state == assoc_normal_state:
                raise HTTPException(status_code=400, detail="Associated channel normal_state must be opposite of main channel")
            
            if req.release_dp_group:
                target_cfg.update({
                    "associate_channel_id": None,
                    "dp_group_id": None
                })
                assoc_entry.update({
                    "associate_channel_id": None,
                    "dp_group_id": None
                })
            else:
                used_groups = set()
                for cfg in channels_map.values():
                    if cfg.get("dp_group_id") and cfg.get("associate_channel_id"):
                        used_groups.add(cfg.get("dp_group_id"))
                
                available_groups = []
                for i in range(1, 9):
                    group_id = f"DP{i}"
                    if group_id not in used_groups:
                        available_groups.append(group_id)
                
                if not available_groups:
                    raise HTTPException(status_code=400, detail="Maximum 8 Double Point groups reached")
                
                group_id = available_groups[0]
                dp_ioa = f"101{int(group_id[2:]) + 14}"
                
                main_ioa = target_cfg.get("ioa") or dp_ioa
                target_cfg.update({
                    "ioa": main_ioa,
                    "dp_group_id": group_id,
                    "associate_channel_id": assoc_id
                })
                
                assoc_entry.update({
                    "ioa": main_ioa,
                    "dp_group_id": group_id,
                    "associate_channel_id": ch_id
                })
                
                channels_map[target_key] = target_cfg
                channels_map[assoc_key] = assoc_entry
        else:
            # Standalone DP
            target_cfg["channel_type"] = "Double Point Parameter"
            target_cfg["normal_state"] = "ON"
            target_cfg["associate_channel_id"] = None
            target_cfg.pop("dp_group_id", None)

    target_cfg = channels_map[target_key]
    if target_cfg.get("timestamp_enable") is not None and target_cfg.get("io_activation_mode") is not None:
        target_cfg["is_enabled"] = target_cfg["timestamp_enable"] and target_cfg.get("io_activation_mode") not in ("0", "0: disabled")

    channel["channels"] = channels_map

    await FRTUModules.update(
        conditions={"id": module_id},
        attribute=attr,
        channel=channel,
    )

    module_info = attr.get(info_key, {})
    general_info = module_info.get("general_info", {})
    slot_number = general_info.get("slot_number")
    if not slot_number:
        raise HTTPException(status_code=500, detail="slot_number not found")

    module_num = int(slot_number) - 3
    serial_channel = f"MODULE_{module_num}"

    dp_pairs_set = set()
    for cfg in channels_map.values():
        if cfg.get("channel_type") != "Double Point Parameter" or not cfg.get("is_enabled"):
            continue
        
        assoc_id = cfg.get("associate_channel_id")
        if not assoc_id:
            continue
        
        assoc_ch = next((c for c in channels_map.values() if c.get("channel_id") == assoc_id), None)
        if not assoc_ch or assoc_ch.get("channel_type") != "Double Point Parameter":
            continue
        
        a = int(cfg["channel_no"])
        b = int(assoc_ch["channel_no"])
        if a != b:
            p1, p2 = (a, b) if a < b else (b, a)
            dp_pairs_set.add(f"{p1},{p2}")

    dp_pairs = sorted(dp_pairs_set, key=lambda x: int(x.split(",")[0]))

    regenerate_module_ini(
        ini_path="rtu_config_iec104_di.ini",
        # ini_path="di.ini",
        serial_channel=serial_channel,
        channels=channels_map,
        dp_pairs=dp_pairs,
    )

    logger.info(f"FRTU di.ini: Slot {slot_number} → {serial_channel}, dp_pairs={dp_pairs}")

    return {
        "status": "success",
        "message": "DI channel configured successfully",
        "device_id": device_id,
        "sub_module_id": str(module_id),
        "channels": channels_map,
        "associateable_channels": associateable_channels,
    }




async def get_di_channel_detail(
    device_id: str,
    device_type: str,
    sub_module_id: str,
    channel_id: str,
    user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
        sub_module_uuid = UUID(sub_module_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id or sub_module_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    dev = devices[0]
    db_type = (
        dev.type.name
        if hasattr(dev.type, "name")
        else (dev.type.value if hasattr(dev.type, "value") else str(dev.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    mods = await FRTUModules.select(id=sub_module_uuid)
    if not mods:
        raise HTTPException(status_code=400, detail="Invalid sub_module_id")
    m = mods[0]
    module_id = m.id
    slot_id = m.slot_id
    ch_blob: Dict[str, Any] = dict(m.channel or {})

    slots = await FRTUSlots.select(id=slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="Module does not belong to this device")

    mtypes = await FRTUModuleType.select(id=m.module_type)
    if not mtypes or mtypes[0].name.strip().upper() != "DI":
        raise HTTPException(status_code=400, detail="Only DI modules supported")

    channels_map: Dict[str, Any] = dict(ch_blob.get("channels") or {})
    if not channels_map:
        raise HTTPException(status_code=404, detail="No channels configured for this module")

    found_key = None
    found_cfg = None
    for key, cfg in channels_map.items():
        if cfg.get("channel_id") == channel_id:
            found_key = key
            found_cfg = cfg
            break

    if not found_cfg:
        raise HTTPException(status_code=404, detail="channel_id not found for this module")

    used_as_assoc_ids: set[str] = set()
    for cfg in channels_map.values():
        assoc_id = cfg.get("associate_channel_id")
        if assoc_id:
            used_as_assoc_ids.add(assoc_id)

    associateable_channels: List[Dict[str, Any]] = []
    for key, cfg in channels_map.items():
        cid = cfg.get("channel_id")
        if cid == channel_id:
            continue
        if cfg.get("channel_type") != "Single Point Parameter":
            continue
        if cid in used_as_assoc_ids:
            continue
        if not cfg.get("is_enabled", False):
            continue
        associateable_channels.append({
            "name": f"DI channel {cfg.get('channel_no')}",
            "channel_id": cid,
            "channel_no": cfg.get("channel_no"),
        })

    return {
        "status": "success",
        "device_id": device_id,
        "sub_module_id": str(module_id),
        "channel_key": found_key,
        "channel": found_cfg,
        "associateable_channels": associateable_channels,
    }


async def configure_module_ioa(
    device_id: str,
    device_type: str,
    sub_module_id: UUID,
    base_ioa: Optional[int] = None,
    channels: Optional[List[Dict[str, str]]] = None,
    # user_id: UUID,
) -> Dict[str, Any]:
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    dev = devices[0]
    db_type = (
        dev.type.name if hasattr(dev.type, "name")
        else (dev.type.value if hasattr(dev.type, "value") else str(dev.type))
    )
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match")

    mods = await FRTUModules.select(id=sub_module_id)
    if not mods:
        raise HTTPException(status_code=400, detail="Invalid sub_module_id")
    m = mods[0]
    module_id = m.id
    slot_id = m.slot_id
    channel_blob: Dict[str, Any] = dict(m.channel or {})
    channels_map: Dict[str, Any] = dict(channel_blob.get("channels") or {})

    slots = await FRTUSlots.select(id=slot_id, device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="Module does not belong to this device")

    mtypes = await FRTUModuleType.select(id=m.module_type)
    if not mtypes or mtypes[0].name.strip().upper() != "DI":
        raise HTTPException(status_code=400, detail="Only DI modules supported")

    attr: Dict[str, Any] = dict(m.attribute or {})
    info_key = "module_di_info"
    module_info = attr.get(info_key, {})
    general_info = module_info.get("general_info", {})
    slot_number = general_info.get("slot_number")
    if not slot_number:
        raise HTTPException(status_code=500, detail="slot_number not found")

    slot_num = int(slot_number)
    calculated_base_ioa = 1000 + (slot_num - 4) * 400
    final_base_ioa = base_ioa or calculated_base_ioa

    ioa_mapping = []
    used_ioas = set()

    for cfg in channels_map.values():
        existing_ioa = cfg.get("ioa")
        if existing_ioa and existing_ioa != "0":
            used_ioas.add(existing_ioa)

    if channels:
        for ch_data in channels:
            ch_no = ch_data.get("channel_no")
            ioa_val = ch_data.get("ioa")
            
            if not ch_no or not ioa_val:
                continue
                
            ch_no_int = int(str(ch_no))
            if not (1 <= ch_no_int <= 16):
                continue
                
            key = f"channel_{ch_no_int}"
            if key not in channels_map:
                continue
                
            if ioa_val in used_ioas and ioa_val != channels_map[key].get("ioa"):
                raise HTTPException(
                    status_code=400,
                    detail=f"IOA {ioa_val} already used by another channel"
                )
                
            channels_map[key]["ioa"] = ioa_val
            ioa_mapping.append({"channel_no": str(ch_no_int), "ioa": ioa_val})
            used_ioas.add(ioa_val)

    else:  
        for ch_no_int in range(1, 17):
            key = f"channel_{ch_no_int}"
            if key not in channels_map:
                continue
                
            ioa_val = f"{final_base_ioa + ch_no_int - 1}"
            
            if ioa_val in used_ioas and ioa_val != channels_map[key].get("ioa"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Auto-generated IOA {ioa_val} conflicts with existing channel"
                )
                
            channels_map[key]["ioa"] = ioa_val
            ioa_mapping.append({"channel_no": str(ch_no_int), "ioa": ioa_val})
            used_ioas.add(ioa_val)

    channel_blob["channels"] = channels_map
    await FRTUModules.update(
        conditions={"id": module_id},
        channel=channel_blob,
    )

    module_num = slot_num - 3
    serial_channel = f"MODULE_{module_num}"
    
    dp_pairs_set = set()
    for cfg in channels_map.values():
        if cfg.get("channel_type") == "Double Point Parameter" and cfg.get("is_enabled"):
            assoc_id = cfg.get("associate_channel_id")
            if assoc_id:
                assoc_ch = next((c for c in channels_map.values() if c.get("channel_id") == assoc_id), None)
                if assoc_ch and assoc_ch.get("channel_type") == "Double Point Parameter":
                    a, b = int(cfg["channel_no"]), int(assoc_ch["channel_no"])
                    p1, p2 = (a, b) if a < b else (b, a)
                    dp_pairs_set.add(f"{p1},{p2}")
    
    dp_pairs = sorted(dp_pairs_set, key=lambda x: int(x.split(",")[0]))

    from src.utils.ini_handler import regenerate_module_ini
    regenerate_module_ini(
        ini_path="rtu_config_iec104_di.ini",
        # ini_path="di.ini",
        serial_channel=serial_channel,
        channels=channels_map,
        dp_pairs=dp_pairs,
    )

    return {
        "status": "success",
        "message": f"Module IOA configured successfully. Base IOA: {final_base_ioa}",
        "device_id": device_id,
        "sub_module_id": str(module_id),
        "slot_number": slot_number,
        "base_ioa": str(final_base_ioa),
        "ioa_mapping": ioa_mapping,
    }

