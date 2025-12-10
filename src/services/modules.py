from typing import List
from uuid import UUID
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots
from src import log

# auto discover helper functions can be added here for auto discover_modules  api
MODULE_TYPE_CACHE: dict[str, UUID] = {}


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


async def _delete_all_modules_for_device(device_id: UUID):
    dev_id_str = str(device_id)
    mods = await FRTUModules.select()
    for m in mods:
        attr = m.attribute or {}
        if attr.get("device_id") == dev_id_str:
            await FRTUModules.delete(m.id)


async def _insert_module(
    device_id: UUID,
    slot_id: UUID,
    logical_slot: int,
    module_type_code: str,
    name: str,
):
    module_type_id = await _get_module_type_id(module_type_code)
    if not module_type_id:
        return
    attr = {
        "device_id": str(device_id),
        "slot_number": logical_slot,
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