from typing import List, Tuple
from uuid import UUID
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src import log

# auto discover helper functions can be added here for auto discover_modules  api
MODULE_TYPE_CACHE: dict[str, UUID] = {}
MODULE_TYPE_REVERSE_CACHE: dict[UUID, str] = {}

async def _get_module_type_id(code: str) -> UUID | None:
    code = code.upper()
    if code in MODULE_TYPE_CACHE:
        return MODULE_TYPE_CACHE[code]
    rows = await FRTUModuleType.select(name=code)
    if not rows:
        log.error(f"[AUTO_DISCOVER] module_type '{code}' not found")
        return None
    mt = rows[0]
    MODULE_TYPE_CACHE[code] = mt.id
    MODULE_TYPE_REVERSE_CACHE[mt.id] = code
    return mt.id


async def _get_slots_for_device(device_id: UUID) -> dict[int, UUID]:
    slots = await FRTUSlots.select(device_id=device_id)
    by_no: dict[int, UUID] = {}
    for s in slots:
        try:
            sn = int(s.name)
        except Exception:
            continue
        if 1 <= sn <= 11:
            by_no[sn] = s.id
    return by_no

async def _get_module_type_code(module_type_id: UUID) -> str | None:
    if module_type_id in MODULE_TYPE_REVERSE_CACHE:
        return MODULE_TYPE_REVERSE_CACHE[module_type_id]
    rows = await FRTUModuleType.select(id=module_type_id)
    if not rows:
        return None
    mt = rows[0]
    code = mt.name.upper()
    MODULE_TYPE_REVERSE_CACHE[module_type_id] = code
    MODULE_TYPE_CACHE[code] = mt.id
    return code

async def _get_modules_for_device(device_id: UUID) -> List[Tuple[int, str]]:
    dev_id_str = str(device_id)
    mods = await FRTUModules.select()
    result: List[Tuple[int, str]] = []
    for m in mods:
        attr = m.attribute or {}
        if attr.get("device_id") != dev_id_str:
            continue
        logical_slot = int(attr.get("slot_number", 0))
        if logical_slot <= 0:
            continue
        code = await _get_module_type_code(m.module_type)
        if not code:
            continue
        result.append((logical_slot, code))
    return result

# async def _delete_all_modules_for_device(device_id: UUID):
#     dev_id_str = str(device_id)
#     mods = await FRTUModules.select()
#     for m in mods:
#         attr = m.attribute or {}
#         if attr.get("device_id") == dev_id_str:
#             await FRTUModules.delete(m.id)


async def _delete_module_by_slot_type(device_id: UUID, logical_slot: int, module_type: str):
    """Delete FRTUModule by device_id, logical_slot, and module_type"""
    module_type_id = await _get_module_type_id(module_type)
    if not module_type_id:
        return
    
    modules = await FRTUModules.select(
        device_id=device_id,
        logical_slot=logical_slot,
        module_type=module_type_id,
    )
    
    for module in modules:
        await FRTUModules.delete(module.id)
        log.debug(f"Deleted module: id={module.id}, slot={logical_slot}, type={module_type}")


async def _get_module_type_id(module_type_code: str) -> UUID | None:
    """Get FRTUModuleType.id by type code (PS/SOM/COM/DI/DO)"""
    types = await FRTUModuleType.select(name=module_type_code)
    return types[0].id if types else None


async def _insert_module(
    device_id: UUID,
    slot_id: UUID,
    logical_slot: int,
    module_type_code: str,
    name: str,
    is_auto: bool = True,
):
    module_type_id = await _get_module_type_id(module_type_code)
    if not module_type_id:
        return
    attr = {
        "device_id": str(device_id),
        "slot_number": logical_slot,
        "is_auto": is_auto,
    }
    await FRTUModules.insert(
        slot_id=slot_id,
        name=name,
        module_type=module_type_id,
        description=None,
        attribute=attr,
        channel={},
    )


# auto discover helper functions can be added here for auto discover_modules_msg api
def _format_slots(slots: List[int]) -> str:
    return " / ".join(str(s) for s in sorted(slots)) if slots else ""

# Helper function to format module list
def _fmt_modules(di_slots: List[int], do_slots: List[int]) -> List[str]:
    modules: List[str] = [
        "Power Supply (1)",
        "Communication Module (2)",
        "SOM Module (3)",
    ]
    for s in sorted(di_slots):
        modules.append(f"Digital Input ({s})")
    for s in sorted(do_slots):
        modules.append(f"Digital Output ({s})")
    return modules

def _get_display_name(module: FRTUModules, module_type: str, idx: int) -> str:
    """Priority: custom name from general_info > auto-numbered fallback"""
    attribute = dict(module.attribute or {})
    info_key = "module_di_info" if module_type == "DI" else "module_do_info"
    module_info = dict(attribute.get(info_key) or {})
    general_info = dict(module_info.get("general_info") or {})
    
    custom_name = general_info.get("name")
    if custom_name:
        return str(custom_name)
    if module_type == "DI":
        return f"Digital Input {idx}"
    elif module_type == "DO":
        return f"Digital Output {idx}"
    else:
        return str(module.name)