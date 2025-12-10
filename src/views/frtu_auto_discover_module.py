from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import Query
from src.enums.FrtuDeviceType import FrtuDeviceType
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.schemas.frtu_auto_discover_module import AutoDiscoverBySitePayload, AutoDiscoverRequest
from src import HttpStatusCode, log
from src.services.modules import _delete_all_modules_for_device, _fmt_modules, _format_slots, _get_slots_for_device, _insert_module
from src.utils.frtu_client import frtu_client



# async def auto_discover_modules(payload: AutoDiscoverRequest, user_id: UUID):
#     entity = payload.entity
#     device_name = entity.name
#     device_type: FrtuDeviceType = entity.type

#     log.info(
#         f"[AUTO_DISCOVER] v1 op={payload.operation} target={payload.target} "
#         f"name={device_name} type={device_type.value} user_id={user_id}"
#     )

#     device, error = await _resolve_device_for_user(
#         user_id=user_id,
#         name=device_name,
#         dev_type=device_type,
#         site_id=None,
#     )
#     if error:
#         return error

#     slots = await FRTUSlots.select(device_id=device.id)
#     slot_count = len(slots)

#     return {
#         "http_code": 200,
#         "code": "AUTO_DISCOVERY_READY",
#         "message": f"Auto discovery can be performed for {device_type.value} '{device.name}'.",
#         "data": {
#             "device_id": str(device.id),
#             "device_name": device.name,
#             "type": device.type,
#             "total_slots": slot_count,
#         },
#     }


async def auto_discover_modules(payload: AutoDiscoverRequest, user_id: UUID):
    entity = payload.entity
    device_name = entity.name.strip()
    device_type: FrtuDeviceType = entity.type

    log.info(
        f"[AUTO_DISCOVER] op={payload.operation} target={payload.target} "
        f"name={device_name} type={device_type.value} user_id={user_id}"
    )

    devices = await FRTUDevices.select(name=device_name, type=device_type.value)
    if not devices:
        return {
            "http_code": 404,
            "code": "DEVICE_NOT_FOUND",
            "message": (
                f"No device found with name '{device_name}' and type "
                f"'{device_type.value}'."
            ),
        }

    device = devices[0]
    device_id = device.id
    device_name_db = device.name

    if not frtu_client.health_check():
        return HttpStatusCode.SERVICE_UNAVAILABLE.response(
            f"FRTU device '{device_name_db}' is not reachable."
        )

    try:
        devids = frtu_client.parse_devids_conf()
    except FileNotFoundError as e:
        log.error(f"devids.conf not found on FRTU: {e}")
        return {
            "http_code": 404,
            "code": "DEVIDS_NOT_FOUND",
            "message": f"devids.conf not found on FRTU device '{device_name_db}'.",
        }
    except Exception as e:
        log.error(f"Failed to parse devids.conf on FRTU: {e}")
        return {
            "http_code": 500,
            "code": "DEVIDS_PARSE_ERROR",
            "message": "Failed to read module information from FRTU.",
        }

    slot_by_number = await _get_slots_for_device(device_id=device_id)
    if len(slot_by_number) != 11:
        log.warning(
            f"[AUTO_DISCOVER] device '{device_name_db}' expected 11 slots, found {len(slot_by_number)}"
        )

    await _delete_all_modules_for_device(device_id=device_id)

    if 1 in slot_by_number:
        await _insert_module(
            device_id=device_id,
            slot_id=slot_by_number[1],
            logical_slot=1,
            module_type_code="PS",
            name="Power Supply",
        )
    if 2 in slot_by_number:
        await _insert_module(
            device_id=device_id,
            slot_id=slot_by_number[2],
            logical_slot=2,
            module_type_code="SOM",
            name="Master Processor",
        )
    if 3 in slot_by_number:
        await _insert_module(
            device_id=device_id,
            slot_id=slot_by_number[3],
            logical_slot=3,
            module_type_code="COM",
            name="Communication",
        )

    di_slots: List[int] = []
    do_slots: List[int] = []

    for m in devids:
        slot_no = int(m.get("slot_no", 0))
        type_flag = int(m.get("type_flag", 0))
        if not (1 <= slot_no <= 8):
            continue

        logical_slot = slot_no + 3
        slot_id = slot_by_number.get(logical_slot)
        if not slot_id:
            continue

        if type_flag == 1:
            di_slots.append(logical_slot)
            await _insert_module(
                device_id=device_id,
                slot_id=slot_id,
                logical_slot=logical_slot,
                module_type_code="DI",
                name="Digital Input",
            )
        elif type_flag == 2:
            do_slots.append(logical_slot)
            await _insert_module(
                device_id=device_id,
                slot_id=slot_id,
                logical_slot=logical_slot,
                module_type_code="DO",
                name="Digital Output",
            )

    return {
        "http_code": 200,
        "code": "AUTO_DISCOVERY_READY",
        "message": f"Auto discovery stored modules for {device_type.value} '{device_name_db}'.",
        "data": {
            "device_id": str(device_id),
            "device_name": device_name_db,
            "type": device_type.value,
        },
    }


# async def auto_discover_modules_by_site(payload: AutoDiscoverBySitePayload, user_id: UUID):
#     site_id = UUID(str(payload.site_id))
#     device_name = payload.name
#     device_type: FrtuDeviceType = payload.type

#     log.info(
#         f"[AUTO_DISCOVER] v2 site_id={site_id} name={device_name} "
#         f"type={device_type.value} user_id={user_id}"
#     )

#     device, error = await _resolve_device_for_user(
#         user_id=user_id,
#         name=device_name,
#         dev_type=device_type,
#         site_id=site_id,
#     )
#     if error:
#         return error

#     slots = await FRTUSlots.select(device_id=device.id)
#     slot_count = len(slots)

#     return {
#         "http_code": 200,
#         "code": "AUTO_DISCOVERY_READY",
#         "message": f"Auto discovery can be performed for {device_type.value} '{device.name}'.",
#         "data": {
#             "device_id": str(device.id),
#             "device_name": device.name,
#             "type": device.type,
#             "site_id": str(site_id),
#             "total_slots": slot_count,
#         },
#     }


async def auto_discover_modules_msg(
    a_name: str,
    a_type: FrtuDeviceType,
    user_id: UUID,
):
    device_name = a_name.strip()
    device_type = a_type

    devices = await FRTUDevices.select(name=device_name, type=device_type.value)
    if not devices:
        return {
            "http_code": 404,
            "code": "DEVICE_NOT_FOUND",
            "message": (
                f"No device found with name '{device_name}' and type "
                f"'{device_type.value}'."
            ),
        }

    device = devices[0]
    device_id = device.id
    device_name_db = device.name

    slots = await FRTUSlots.select(device_id=device_id)
    slot_id_to_logical: dict[UUID, int] = {}
    for s in slots:
        try:
            sn = int(s.name)
        except Exception:
            continue
        if 1 <= sn <= 11:
            slot_id_to_logical[s.id] = sn

    total_slots = 11

    mods = await FRTUModules.select()
    mods_for_device = []
    dev_id_str = str(device_id)
    for m in mods:
        attr = m.attribute or {}
        if attr.get("device_id") == dev_id_str:
            mods_for_device.append(m)

    type_rows = await FRTUModuleType.select()
    type_map: dict[UUID, str] = {t.id: t.name.upper() for t in type_rows}

    ps_slots: List[int] = []
    som_slots: List[int] = []
    com_slots: List[int] = []
    di_slots: List[int] = []
    do_slots: List[int] = []

    for m in mods_for_device:
        tcode = type_map.get(m.module_type, "").upper()
        logical_slot = slot_id_to_logical.get(m.slot_id)
        if not isinstance(logical_slot, int):
            continue
        if tcode == "PS":
            ps_slots.append(logical_slot)
        elif tcode == "SOM":
            som_slots.append(logical_slot)
        elif tcode == "COM":
            com_slots.append(logical_slot)
        elif tcode == "DI":
            di_slots.append(logical_slot)
        elif tcode == "DO":
            do_slots.append(logical_slot)

    used_slots = set(ps_slots + som_slots + com_slots + di_slots + do_slots)
    all_slots = set(range(1, total_slots + 1))
    empty_slots_list = sorted(all_slots - used_slots)

    modules_block = {
        "Power Supply Identified in Slot": _format_slots(ps_slots) or "1",
        "Communication Module Identified in Slot": _format_slots(com_slots) or "2",
        "SOM Module Identified in Slot": _format_slots(som_slots) or "3",
        "DI Module Identified in Slots": _format_slots(di_slots),
        "DO Module Identified in Slots": _format_slots(do_slots),
    }

    return {
        "http_code": 200,
        "code": "AUTO_DISCOVERY_SUMMARY",
        "message": f"Modules discovered successfully for {device_type.value} '{device_name_db}'.",
        "frtuName": device_name_db,
        "frtuType": device_type.value,
        "totalSlots": total_slots,
        "emptySlots": len(empty_slots_list),
        "totalDI": str(len(di_slots)),
        "totalDO": str(len(do_slots)),
        "modules": modules_block,
    }


async def auto_discover_modules_list(
    a_name: str,
    a_type: FrtuDeviceType,
    user_id: UUID,
):
    device_name = a_name.strip()
    device_type = a_type

    devices = await FRTUDevices.select(name=device_name, type=device_type.value)
    if not devices:
        return {
            "http_code": 404,
            "code": "DEVICE_NOT_FOUND",
            "message": (
                f"No device found with name '{device_name}' and type "
                f"'{device_type.value}'."
            )
        }

    device = devices[0]
    device_id = device.id
    device_name_db = device.name

    slots = await FRTUSlots.select(device_id=device_id)
    slot_id_to_no: dict[UUID, int] = {}
    for s in slots:
        try:
            sn = int(s.name)
        except Exception:
            continue
        if 1 <= sn <= 11:
            slot_id_to_no[s.id] = sn

    mods = await FRTUModules.select()
    dev_id_str = str(device_id)
    mods_for_device = []
    for m in mods:
        attr = m.attribute or {}
        if attr.get("device_id") == dev_id_str:
            mods_for_device.append(m)

    type_rows = await FRTUModuleType.select()
    type_map: dict[UUID, str] = {t.id: t.name.upper() for t in type_rows}

    di_slots: List[int] = []
    do_slots: List[int] = []
    fixed_slots = {1, 2, 3}
    total_slots = 11

    for m in mods_for_device:
        tcode = type_map.get(m.module_type, "").upper()
        logical_no = slot_id_to_no.get(m.slot_id)
        if not isinstance(logical_no, int):
            continue
        if tcode == "DI":
            di_slots.append(logical_no)
        elif tcode == "DO":
            do_slots.append(logical_no)

    used_slots = fixed_slots.union(di_slots).union(do_slots)
    all_slots = set(range(1, total_slots + 1))
    empty_slots = sorted(all_slots - used_slots)

    return {
        "http_code": 200,
        "code": "AUTO_DISCOVERY_LIST",
        "message": f"Modules listed successfully for {device_type.value} '{device_name_db}'.",
        "frtuName": device_name_db,
        "frtuType": device_type.value,
        "totalSlots": str(total_slots),
        "emptySlots": str(len(empty_slots)),
        "totalDI": str(len(di_slots)),
        "totalDO": str(len(do_slots)),
        "modules": _fmt_modules(di_slots, do_slots),
    }

