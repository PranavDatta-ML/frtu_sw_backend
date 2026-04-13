from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import Query
from src.enums.FrtuDeviceType import FrtuDeviceType
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_auto_discover_module import  AutoDiscoverRequest
from src import HttpStatusCode, log
from src.services.modules import  _delete_module_by_slot_type, _delete_stale_di_do_modules, _fmt_modules, _format_slots, _get_module_type_code, _get_modules_for_device, _get_slots_for_device, _insert_module, _move_module_to_new_slot, reconcile_di_do_modules
from src.utils.frtu_client import frtu_client

# ----------------------------- Working but delete stale and delete configuration -----------------------
# async def auto_discover_modules(payload: AutoDiscoverRequest, user_id: UUID):
#     entity = payload.entity
#     device_name = entity.name.strip()
#     device_type: FrtuDeviceType = entity.type

#     log.info(
#         f"[AUTO_DISCOVER] name={device_name} type={device_type.value} user={user_id}"
#     )

#     devices = await FRTUDevices.select(
#         name=device_name,
#         type=device_type.value,
#     )
#     if not devices:
#         return HttpStatusCode.NOT_FOUND.response("Device not found")

#     device = devices[0]
#     device_id: UUID = device.id

#     if not frtu_client.health_check():
#         return HttpStatusCode.SERVICE_UNAVAILABLE.response(
#             f"FRTU device '{device_name}' is not reachable"
#         )

#     devids = frtu_client.parse_devids_conf()

#     slot_by_number = await _get_slots_for_device(device_id)
#     if not slot_by_number:
#         return HttpStatusCode.BAD_REQUEST.response("No slots found for device")

#     all_modules = await FRTUModules.select()
#     device_modules = []

#     for m in all_modules:
#         attr = m.attribute or {}
#         if attr.get("device_id") == str(device_id):
#             device_modules.append(m)

#     existing: Dict[Tuple[int, str], FRTUModules] = {}

#     for m in device_modules:
#         slot_id = m.slot_id
#         slot_no = None

#         for sn, sid in slot_by_number.items():
#             if sid == slot_id:
#                 slot_no = sn
#                 break

#         if slot_no is None:
#             continue

#         code = await _get_module_type_code(m.module_type)
#         if not code:
#             continue

#         existing[(slot_no, code)] = m

#     desired_di_do: Set[Tuple[int, str]] = set()

#     for d in devids:
#         logical_slot = int(d["slot"])          # already 4–11
#         type_flag = int(d["module_type"])      # 1=DI, 2=DO

#         if logical_slot not in slot_by_number:
#             continue

#         if type_flag == 1:
#             desired_di_do.add((logical_slot, "DI"))
#         elif type_flag == 2:
#             desired_di_do.add((logical_slot, "DO"))

#     fixed_modules = {
#         1: ("PS", "Power Supply"),
#         2: ("SOM", "Master Processor"),
#         3: ("COM", "Communication"),
#     }

#     for slot_no, (code, name) in fixed_modules.items():
#         key = (slot_no, code)
#         if key in existing:
#             continue

#         slot_id = slot_by_number.get(slot_no)
#         if not slot_id:
#             continue

#         await _insert_module(
#             device_id=device_id,
#             slot_id=slot_id,
#             logical_slot=slot_no,
#             module_type_code=code,
#             name=name,
#         )

#         log.info(f"[AUTO_DISCOVER] Inserted {code} at slot {slot_no}")

#     for slot_no, code in desired_di_do:
#         key = (slot_no, code)
#         if key in existing:
#             continue

#         slot_id = slot_by_number[slot_no]

#         await _insert_module(
#             device_id=device_id,
#             slot_id=slot_id,
#             logical_slot=slot_no,
#             module_type_code=code,
#             name="Digital Input" if code == "DI" else "Digital Output",
#         )

#         log.info(f"[AUTO_DISCOVER] Inserted {code} at slot {slot_no}")

#     delete_ids = []

#     for (slot_no, code), module in existing.items():
#         if code not in {"DI", "DO"}:
#             continue

#         if (slot_no, code) not in desired_di_do:
#             delete_ids.append(module.id)

#     for mid in delete_ids:
#         await FRTUModules.delete(conditions={"id": mid})

#     log.info(
#         f"[AUTO_DISCOVER] Deleted {len(delete_ids)} stale DI/DO modules for device {device_name}"
#     )

#     return {
#         "http_code": 200,
#         "code": "AUTO_DISCOVERY_READY",
#         "message": (
#             f"Auto discovery completed for '{device_name}'. "
#             f"Deleted {len(delete_ids)} stale DI/DO modules."
#         ),
#         "data": {
#             "device_id": str(device_id),
#             "device_name": device_name,
#             "type": device_type.value,
#         },
#     }

# ----------------------------- Working properly fine device wise and also save configuration as it is -----------------------
async def auto_discover_modules(payload: AutoDiscoverRequest, user_id: UUID):
    entity = payload.entity
    device_name = entity.name.strip()
    device_type: FrtuDeviceType = entity.type

    log.info(f"[AUTO_DISCOVER] name={device_name} type={device_type.value} user={user_id}")

    devices = await FRTUDevices.select(name=device_name, type=device_type.value)
    if not devices:
        return HttpStatusCode.NOT_FOUND.response("Device not found")

    device = devices[0]
    device_id: UUID = device.id

    if not frtu_client.health_check():
        return HttpStatusCode.SERVICE_UNAVAILABLE.response(
            f"FRTU device '{device_name}' is not reachable"
        )

    try:
        devids = frtu_client.parse_devids_conf()
    # except FileNotFoundError as e:
    #     return HttpStatusCode.SERVICE_UNAVAILABLE.response(str(e))

    except FileNotFoundError:
        devids = []  # devids.conf not yet created on device; no DI/DO modules
    slot_by_number = await _get_slots_for_device(device_id)

    if not slot_by_number:
        return HttpStatusCode.BAD_REQUEST.response("No slots found for device")

    all_modules = await FRTUModules.select()

    device_modules = []
    for m in all_modules:
        attr = m.attribute or {}
        if attr.get("device_id") == str(device_id):
            device_modules.append(m)

    existing: Dict[Tuple[int, str], UUID] = {}

    for m in device_modules:
        slot_id = m.slot_id
        slot_no = None

        for sn, sid in slot_by_number.items():
            if sid == slot_id:
                slot_no = sn
                break

        if slot_no is None:
            continue

        code = await _get_module_type_code(m.module_type)
        if not code:
            continue

        existing[(slot_no, code)] = m.id

    desired_di_do: Set[Tuple[int, str]] = set()

    for d in devids:
        raw_slot = d.get("slot") or d.get("slot_number") or d.get("slot_no")
        raw_type = d.get("module_type") or d.get("type_flag")
        if raw_slot is None or raw_type is None:
            log.warning(f"[AUTO_DISCOVER] Skipping devids entry with unexpected keys: {d}")
            continue
        logical_slot = int(raw_slot)
        type_flag = int(raw_type)

        if logical_slot not in slot_by_number:
            continue

        if type_flag == 1:
            desired_di_do.add((logical_slot, "DI"))
        elif type_flag == 2:
            desired_di_do.add((logical_slot, "DO"))

    fixed_modules = {
        1: ("PS", "Power Supply"),
        2: ("SOM", "Master Processor"),
        3: ("COM", "Communication"),
    }

    for slot_no, (code, name) in fixed_modules.items():
        key = (slot_no, code)
        if key in existing:
            continue

        slot_id = slot_by_number.get(slot_no)
        if not slot_id:
            continue
        if slot_no == 3:
            existing_in_slot = await FRTUModules.select(slot_id=slot_id)
            if existing_in_slot:
                log.info(f"[AUTO_DISCOVER] Slot 3 already occupied. Skipping COM insert.")
                continue

        key = (slot_no, code)
        if key in existing:
            continue
        await _insert_module(
            device_id=device_id,
            slot_id=slot_id,
            logical_slot=slot_no,
            module_type_code=code,
            name=name,
        )

        log.info(f"[AUTO_DISCOVER] Inserted {code} at slot {slot_no}")

    for slot_no, code in desired_di_do:
        key = (slot_no, code)
        if key in existing:
            continue

        slot_id = slot_by_number[slot_no]

        await _insert_module(
            device_id=device_id,
            slot_id=slot_id,
            logical_slot=slot_no,
            module_type_code=code,
            name="Digital Input" if code == "DI" else "Digital Output",
        )

        log.info(f"[AUTO_DISCOVER] Inserted {code} at slot {slot_no}")

    delete_ids = []

    for (slot_no, code), module_id in existing.items():
        if code not in {"DI", "DO"}:
            continue

        if (slot_no, code) not in desired_di_do:
            delete_ids.append(module_id)

    for mid in delete_ids:
        await FRTUModules.delete(conditions={"id": mid})

    log.info(f"[AUTO_DISCOVER] Deleted {len(delete_ids)} stale DI/DO modules for device {device_name}")

    return {
        "http_code": 200,
        "code": "AUTO_DISCOVERY_READY",
        "message": (
            f"Auto discovery completed for '{device_name}'. "
            f"Deleted {len(delete_ids)} stale DI/DO modules."
        ),
        "data": {
            "device_id": str(device_id),
            "device_name": device_name,
            "type": device_type.value,
        },
    }


# ----------------------------- Works but face issue delete configuration of modules -----------------------
# async def auto_discover_modules(payload: AutoDiscoverRequest, user_id: UUID):
#     entity = payload.entity
#     device_name = entity.name.strip()
#     device_type: FrtuDeviceType = entity.type

#     log.info(
#         f"[AUTO_DISCOVER] op={payload.operation} target={payload.target} "
#         f"name={device_name} type={device_type.value} user_id={user_id}"
#     )

#     devices = await FRTUDevices.select(name=device_name, type=device_type.value)
#     if not devices:
#         return {
#             "http_code": 404,
#             "code": "DEVICE_NOT_FOUND",
#             "message": (
#                 f"No device found with name '{device_name}' and type "
#                 f"'{device_type.value}'."
#             ),
#         }

#     device = devices[0]
#     device_id: UUID = device.id
#     device_name_db: str = device.name

#     if not frtu_client.health_check():
#         return HttpStatusCode.SERVICE_UNAVAILABLE.response(
#             f"FRTU device '{device_name_db}' is not reachable."
#         )

#     try:
#         devids = frtu_client.parse_devids_conf()
#     except FileNotFoundError as e:
#         log.error(f"devids.conf not found on FRTU: {e}")
#         return {
#             "http_code": 404,
#             "code": "DEVIDS_NOT_FOUND",
#             "message": f"devids.conf not found on FRTU device '{device_name_db}'.",
#         }
#     except Exception as e:
#         log.error(f"Failed to parse devids.conf on FRTU: {e}")
#         return {
#             "http_code": 500,
#             "code": "DEVIDS_PARSE_ERROR",
#             "message": "Failed to read module information from FRTU.",
#         }

#     slot_by_number = await _get_slots_for_device(device_id=device_id)
#     if len(slot_by_number) != 11:
#         log.warning(
#             f"[AUTO_DISCOVER] device '{device_name_db}' expected 11 slots, found {len(slot_by_number)}"
#         )

#     existing_pairs = await _get_modules_for_device(device_id=device_id)
#     existing_keys = set(existing_pairs)

#     desired_di_do: set[tuple[int, str]] = set()

#     def should_insert(logical_slot: int, module_type_code: str) -> bool:
#         return (logical_slot, module_type_code) not in existing_keys

#     if 1 in slot_by_number and should_insert(1, "PS"):
#         await _insert_module(
#             device_id=device_id,
#             slot_id=slot_by_number[1],
#             logical_slot=1,
#             module_type_code="PS",
#             name="Power Supply",
#         )
#         existing_keys.add((1, "PS"))

#     if 2 in slot_by_number and should_insert(2, "SOM"):
#         await _insert_module(
#             device_id=device_id,
#             slot_id=slot_by_number[2],
#             logical_slot=2,
#             module_type_code="SOM",
#             name="Master Processor",
#         )
#         existing_keys.add((2, "SOM"))

#     if 3 in slot_by_number and should_insert(3, "COM"):
#         await _insert_module(
#             device_id=device_id,
#             slot_id=slot_by_number[3],
#             logical_slot=3,
#             module_type_code="COM",
#             name="Communication",
#         )
#         existing_keys.add((3, "COM"))

#     # for m in devids:
#     #     slot_no = int(m.get("slot_no", 0))
#     #     type_flag = int(m.get("type_flag", 0))
#     #     if not (1 <= slot_no <= 8):
#     #         continue

#     #     logical_slot = slot_no + 3
#     for m in devids:
#         logical_slot = int(m["slot"])          # already 4–11
#         type_flag = int(m["module_type"])      # 1 = DI, 2 = DO

#         slot_id = slot_by_number.get(logical_slot)
#         if not slot_id:
#             continue

#         module_key = (logical_slot, "DI" if type_flag == 1 else "DO")
#         desired_di_do.add(module_key)

#         if type_flag == 1 and should_insert(logical_slot, "DI"):
#             await _insert_module(
#                 device_id=device_id,
#                 slot_id=slot_id,
#                 logical_slot=logical_slot,
#                 module_type_code="DI",
#                 name="Digital Input",
#             )
#             existing_keys.add((logical_slot, "DI"))

#         elif type_flag == 2 and should_insert(logical_slot, "DO"):
#             await _insert_module(
#                 device_id=device_id,
#                 slot_id=slot_id,
#                 logical_slot=logical_slot,
#                 module_type_code="DO",
#                 name="Digital Output",
#             )
#             existing_keys.add((logical_slot, "DO"))
#         slot_id = slot_by_number.get(logical_slot)
#         if not slot_id:
#             continue

#         module_key = (logical_slot, "DI" if type_flag == 1 else "DO")
#         desired_di_do.add(module_key)

#         if type_flag == 1 and should_insert(logical_slot, "DI"):
#             await _insert_module(
#                 device_id=device_id,
#                 slot_id=slot_id,
#                 logical_slot=logical_slot,
#                 module_type_code="DI",
#                 name="Digital Input",
#             )
#             existing_keys.add((logical_slot, "DI"))
#         elif type_flag == 2 and should_insert(logical_slot, "DO"):
#             await _insert_module(
#                 device_id=device_id,
#                 slot_id=slot_id,
#                 logical_slot=logical_slot,
#                 module_type_code="DO",
#                 name="Digital Output",
#             )
#             existing_keys.add((logical_slot, "DO"))

#     deleted_count = await _delete_stale_di_do_modules(device_id, desired_di_do)
#     log.info(f"[AUTO_DISCOVER] Deleted {deleted_count} stale DI/DO modules")

#     return {
#         "http_code": 200,
#         "code": "AUTO_DISCOVERY_READY",
#         "message": f"Auto discovery reconciled modules for {device_type.value} '{device_name_db}'. Deleted {deleted_count} stale modules.",
#         "data": {
#             "device_id": str(device_id),
#             "device_name": device_name_db,
#             "type": device_type.value,
#         },
#     }

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

