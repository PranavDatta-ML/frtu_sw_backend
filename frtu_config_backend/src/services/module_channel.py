import re
from typing import Any, Dict
from uuid import UUID

from fastapi import HTTPException

from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_slots import FRTUSlots


async def _ensure_di_module_state(device_id: UUID, module_id: UUID) -> Dict[str, Any]:
    devices = await FRTUDevices.select(id=device_id)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")

    modules = await FRTUModules.select(id=module_id)
    if not modules:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    m = modules[0]

    slot_id = m.slot_id
    attr: Dict[str, Any] = dict(m.attribute or {})
    channel: Dict[str, Any] = dict(m.channel or {}) if getattr(m, "channel", None) else {}

    slots = await FRTUSlots.select(id=slot_id, device_id=device_id)
    if not slots:
        raise HTTPException(status_code=400, detail="Module does not belong to this device")

    mtypes = await FRTUModuleType.select(id=m.module_type)
    if not mtypes or mtypes[0].name.strip().upper() != "DI":
        raise HTTPException(status_code=400, detail="Only DI modules supported")

    info_key = "module_di_info"
    if info_key not in attr or "general_info" not in (attr.get(info_key) or {}):
        raise HTTPException(
            status_code=400,
            detail="General information must be configured for this module before channel configuration",
        )

    return {
        "module_id": m.id,
        "attribute": attr,
        "channel": channel,
        "info_key": info_key,
    }

def _parse_assoc_no(label: str) -> int:
    m = re.search(r"(\d+)", label or "")
    if not m:
        raise ValueError("Invalid associate_channel_no format")
    return int(m.group(1))


