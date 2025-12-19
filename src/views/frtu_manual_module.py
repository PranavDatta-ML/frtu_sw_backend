import asyncio
import os
import subprocess
from typing import Any, Dict, List
from fastapi import HTTPException, Query, Request, Header, Depends, status
from datetime import datetime, timezone
from uuid import UUID
from fastapi.responses import JSONResponse
from src.core.settings import Settings
from src.core.status_codes import HttpStatusCode
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_master import FRTUModuleMaster
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_manual_module import ConfigureModuleManuallyRequest, GetConfiguredModuleResponse
from src.schemas.frtu_modules import AddModuleAutoRequest, AddModuleManuallyRequest, DeviceModuleItem, DeviceModulesResponse
from src.utils import frtu_client
from src.utils.access_token import decode_token
from src.utils.config_parser import  update_version_conf
from src.utils.frtu_client import frtu_client


async def get_module_list_view():
    try:
        modules = await FRTUModuleMaster.select()

        module_items = [
            {
                "module_id": str(m.id),
                "module_name": m.name,
                # "slot_id": idx + 1,   # or use m.slot_id if you have a column
            }
            for idx, m in enumerate(modules)
        ]

        return {
            "status": "success",
            "http_code": 200,
            "message": "Module list fetched successfully",
            "modules": module_items,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch module list: {e}",
        )
    
async def add_module(
    device_id: str,
    device_type: str,
    payload: AddModuleAutoRequest,
    user_id: UUID,
):
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device_id format",
        )

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
        raise HTTPException(
            status_code=400,
            detail="Device type does not match for this device_id",
        )

    masters = await FRTUModuleMaster.select(id=payload.module_id)
    if not masters:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    master = masters[0]

    requested_type = payload.module_type.strip().upper()
    master_name = master.name.upper()

    if requested_type == "DI":
        if "DIGITAL INPUT" not in master_name and "DI " not in master_name and not master_name.startswith("DI"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="module_type must be DI for this module_id",
            )

    if requested_type == "DO":
        if "DIGITAL OUTPUT" not in master_name and "DO " not in master_name and not master_name.startswith("DO"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="module_type must be DO for this module_id",
            )

    slots: List[FRTUSlots] = await FRTUSlots.select(device_id=device_uuid)
    if not slots:
        raise HTTPException(status_code=400, detail="No slots available for this device")
    slot_data = [
        {"id": s.id, "name": str(s.name)}
        for s in slots
    ]
    slot_ids = [s["id"] for s in slot_data]

    existing_modules: List[FRTUModules] = await FRTUModules.select(slot_id=slot_ids)
    occupied = {m.slot_id for m in existing_modules}

    free_slot = None
    for s in sorted(slot_data, key=lambda x: int(x["name"])):
        if s["id"] not in occupied:
            free_slot = s
            break

    if not free_slot:
        raise HTTPException(status_code=400, detail="No free slot available")

    try:
        slot_number = int(free_slot["name"])
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot name format in frtu_slots",
        )

    module_types = await FRTUModuleType.select(name=requested_type)
    if not module_types:
        raise HTTPException(status_code=400, detail="Invalid module_type")
    module_type_obj = module_types[0]

    try:
        obj = await FRTUModules.insert(
            slot_id=free_slot["id"],
            name=master.name,
            module_type=module_type_obj.id,
            description=getattr(master, "description", "") or "",
            attribute=getattr(master, "attribute", None),
            channel=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save module: {e}",
        )

    try:
        await asyncio.to_thread(
            frtu_client.update_devids_conf,
            slot_number,
            requested_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Module saved but failed to update devids.conf: {e}",
        )

    return {
        "status": "success",
        "http_code": 201,
        "message": "Module added automatically to next free slot",
        "data": {
            "id": str(obj.id),
            "slot_id": str(obj.slot_id),
            "slot_name": free_slot["name"],
            "name": obj.name,
            "module_type": requested_type,
            "description": obj.description,
        },
    }

# ------------------- Add Module Manually to Slot ----------------
async def add_module_manually(
    device_id: str,
    device_type: str,
    payload: AddModuleManuallyRequest,
    user_id: UUID,
):
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device_id format",
        )

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
        raise HTTPException(
            status_code=400,
            detail="Device type does not match for this device_id",
        )

    masters = await FRTUModuleMaster.select(id=payload.module_id)
    if not masters:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    master = masters[0]

    requested_type = payload.module_type.strip().upper()
    master_name = master.name.upper()

    if requested_type == "DI":
        if "DIGITAL INPUT" not in master_name and "DI " not in master_name and not master_name.startswith("DI"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="module_type must be DI for this module_id",
            )

    if requested_type == "DO":
        if "DIGITAL OUTPUT" not in master_name and "DO " not in master_name and not master_name.startswith("DO"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="module_type must be DO for this module_id",
            )

    slots = await FRTUSlots.select(
        id=payload.slot_id,
        device_id=device_uuid,
    )
    if not slots:
        raise HTTPException(
            status_code=400,
            detail="Given slot_id does not belong to this device",
        )
    slot = slots[0]

    try:
        slot_number = int(str(slot.name))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot name format in frtu_slots",
        )

    existing = await FRTUModules.select(slot_id=payload.slot_id)
    if existing:
        raise HTTPException(status_code=400, detail="Slot already occupied")

    module_types = await FRTUModuleType.select(name=requested_type)
    if not module_types:
        raise HTTPException(status_code=400, detail="Invalid module_type")
    module_type_obj = module_types[0]

    try:
        obj = await FRTUModules.insert(
            slot_id=payload.slot_id,
            name=master.name,
            module_type=module_type_obj.id,
            description=getattr(master, "description", "") or "",
            attribute=getattr(master, "attribute", None),
            channel=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save module: {e}",
        )

    try:
        await asyncio.to_thread(
            frtu_client.update_devids_conf,
            slot_number,       
            requested_type,     
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Module saved but failed to update devids.conf: {e}",
        )

    return {
        "status": "success",
        "http_code": 201,
        "message": "Module added manually",
        "data": {
            "id": str(obj.id),
            "slot_id": str(obj.slot_id),
            "name": obj.name,
            "module_type": requested_type,
            "description": obj.description,
        },
    }

# ----------------- get modules list using payload module_id and module_type --------------
async def get_device_modules(
    device_id: str,
    device_type: str,
    is_auto: bool | None,
) -> DeviceModulesResponse:
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
        raise HTTPException(
            status_code=400,
            detail="Device type does not match for this device_id",
        )

    slots: List[FRTUSlots] = await FRTUSlots.select(device_id=device_uuid)
    if not slots:
        return DeviceModulesResponse(
            status="success",
            device_id=device_uuid,
            device_type=device_type,
            is_auto=is_auto,
            modules=[],
        )

    slot_ids = [s.id for s in slots]
    modules: List[FRTUModules] = await FRTUModules.select(slot_id=slot_ids)
    if not modules:
        return DeviceModulesResponse(
            status="success",
            device_id=device_uuid,
            device_type=device_type,
            is_auto=is_auto,
            modules=[],
        )
    module_type_ids = [m.module_type for m in modules]
    types = await FRTUModuleType.select(id=module_type_ids) if module_type_ids else []
    type_by_id = {t.id: t for t in types}

    if is_auto is not None:
        filtered: List[FRTUModules] = []
        for m in modules:
            t = type_by_id.get(m.module_type)
            type_name = t.name if t else None
            if not type_name:
                continue

            upper_type = type_name.strip().upper()
            if upper_type in ("PS", "SOM", "COM"):
                filtered.append(m)
                continue
            # attr = m.attribute or {}
            # raw_flag = attr.get("is_auto")
            # flag = True if raw_flag is None else bool(raw_flag)

            # if is_auto is True:
            #     if flag is True:
            #         filtered.append(m)
            # else: 
            #     if flag is False:
            #         filtered.append(m)
            if is_auto is False and upper_type in ("DI", "DO"):
                filtered.append(m)

        modules = filtered
        if not modules:
            return DeviceModulesResponse(
                status="success",
                device_id=device_uuid,
                device_type=device_type,
                is_auto=is_auto,
                modules=[],
            )
    masters = await FRTUModuleMaster.select()
    master_by_name = {mm.name.strip().upper(): mm for mm in masters}
    di_master = master_by_name.get("DIGITAL INPUT")
    do_master = master_by_name.get("DIGITAL OUTPUT")

    flat_modules: List[Dict[str, Any]] = []
    di_raw: List[FRTUModules] = []
    do_raw: List[FRTUModules] = []

    for m in modules:
        t = type_by_id.get(m.module_type)
        type_name = t.name if t else None
        if not type_name:
            continue

        upper_type = type_name.strip().upper()
        module_name = m.name

        if upper_type in ["PS", "SOM", "COM"]:
            flat_modules.append(
                {
                    "slot_id": str(m.slot_id),
                    "module_id": str(m.id),  # frtu_modules.id
                    "module_type": upper_type,
                    "module_name": module_name,
                }
            )
        elif upper_type == "DI":
            di_raw.append(m)
        elif upper_type == "DO":
            do_raw.append(m)

    modules_list: List[Dict[str, Any]] = []
    modules_list.extend(flat_modules)

    if di_raw:
        modules_list.append(
            {
                "module_name": "Digital Input",
                "module_type": "DI",
                "module_id": str(di_master.id) if di_master else "",
                "di_modules": [
                    {
                        "slot_id": str(m.slot_id),
                        "di_module_id": str(m.id),  # frtu_modules.id
                        "module_name": f"Digital Input {idx}",
                    }
                    for idx, m in enumerate(di_raw, start=1)
                ],
            }
        )

    if do_raw:
        modules_list.append(
            {
                "module_name": "Digital Output",
                "module_type": "DO",
                "module_id": str(do_master.id) if do_master else "",
                "do_modules": [
                    {
                        "slot_id": str(m.slot_id),
                        "do_module_id": str(m.id),  # frtu_modules.id
                        "module_name": f"Digital Output {idx}",
                    }
                    for idx, m in enumerate(do_raw, start=1)
                ],
            }
        )

    return DeviceModulesResponse(
        status="success",
        device_id=device_uuid,
        device_type=device_type,
        is_auto=is_auto,
        modules=modules_list,
    )

# ------------------- Configure Module Manually in Slot ----------------
FIXED_MASTER_SLOTS = {
    "PS": {"slot_number": 1, "card_type": "Power Supply"},
    "SOM": {"slot_number": 2, "card_type": "Master Processor"},
}
async def configure_module_manually(
    device_id: str,
    device_type: str,
    payload: ConfigureModuleManuallyRequest,
    user_id: UUID,
):
    requested_type = payload.module_type.strip().upper()
    if requested_type not in ("PS", "SOM"):
        raise HTTPException(status_code=400, detail="Only PS and SOM supported")

    if not payload.slot_info and not payload.category_info:
        raise HTTPException(status_code=400, detail="Either slot_info or category_info must be provided")

    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    device = devices[0]
    db_type = getattr(device.type, "name", str(device.type))
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    modules = await FRTUModules.select(id=payload.module_id)
    if not modules:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    module = modules[0]

    module_id_value = module.id
    module_slot_id = module.slot_id
    module_name_value = module.name
    module_attr = module.attribute or {}

    slots = await FRTUSlots.select(device_id=device_uuid, id=module_slot_id)
    if not slots:
        raise HTTPException(status_code=400, detail="Given module does not belong to this device")
    slot = slots[0]
    slot_name_value = str(slot.name)
    try:
        actual_slot_no = int(slot_name_value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid slot name format in frtu_slots")

    fixed = FIXED_MASTER_SLOTS[requested_type]
    required_slot = fixed["slot_number"]
    if actual_slot_no != required_slot:
        raise HTTPException(status_code=400, detail=f"{fixed['card_type']} must be in slot {required_slot}")
    card_type = fixed["card_type"]

    if payload.category_info and "slot_info" not in module_attr and not payload.slot_info:
        raise HTTPException(status_code=400, detail="Configure slot_info first, then category_info")

    attr: Dict[str, Any] = dict(module_attr)

    if payload.slot_info is not None:
        slot_info = dict(attr.get("slot_info") or {})
        slot_info.update(dict(payload.slot_info))
        slot_info["slot_number"] = actual_slot_no
        slot_info["slot_id"] = str(module_slot_id)
        slot_info["card_type"] = card_type
        slot_info["module_name"] = module_name_value
        attr["slot_info"] = slot_info

    if payload.category_info is not None:
        if "slot_info" not in attr:
            raise HTTPException(status_code=400, detail="Configure slot_info first for this module")
        category_info = dict(attr.get("category_info") or {})
        category_info.update(dict(payload.category_info))
        attr["category_info"] = category_info

    await FRTUModules.update(
        # row_id=module_id_value,  # use the parameter your Base.update uses as filter
        conditions={"id": module_id_value},
        attribute=attr,
    )

    return {
        "status": "success",
        "http_code": 200,
        "message": "Module configured manually",
        # "data": {
        #     "module_row_id": str(module_id_value),
        #     "module_type": requested_type,
        #     "slot_number": actual_slot_no,
        #     "card_type": card_type,
        #     "attribute": attr,
        # },
    }


# -------------------------------- get manually configured module list view ------------------
# view
async def get_configured_module(
    device_id: str,
    device_type: str,
    module_id: UUID,
) -> GetConfiguredModuleResponse:
    try:
        device_uuid = UUID(device_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    devices = await FRTUDevices.select(id=device_uuid)
    if not devices:
        raise HTTPException(status_code=400, detail="Invalid device_id")
    device = devices[0]
    db_type = getattr(device.type, "name", str(device.type))
    if db_type.strip().upper() != device_type.strip().upper():
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    modules = await FRTUModules.select(id=module_id)
    if not modules:
        raise HTTPException(status_code=400, detail="Invalid module_id")
    module = modules[0]

    if not module.slot_id:
        raise HTTPException(status_code=400, detail="Module not placed in any slot")

    slots = await FRTUSlots.select(device_id=device_uuid, id=module.slot_id)
    if not slots:
        raise HTTPException(status_code=400, detail="Module does not belong to this device")
    slot = slots[0]

    try:
        slot_number = int(str(slot.name))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid slot name format in frtu_slots")

    mtypes = await FRTUModuleType.select(id=module.module_type)
    module_type_name = mtypes[0].name if mtypes else ""

    if module_type_name not in ("PS", "SOM"):
        raise HTTPException(status_code=400, detail="This supports  only Power Supply (PS) and Master Processor (SOM) modules. Use the specific configuration API for other module types.")

    attr = module.attribute or {}
    slot_info = attr.get("slot_info") or None
    category_info = attr.get("category_info") or None

    fixed = FIXED_MASTER_SLOTS[module_type_name]
    base_slot_info = {
        "slot_number": fixed["slot_number"],
        "slot_id": str(module.slot_id),
        "card_type": fixed["card_type"],
        "module_name": module.name,
    }

    if slot_info is None:
        slot_info = base_slot_info
    else:
        merged = dict(base_slot_info)
        merged.update(slot_info)
        slot_info = merged

    return GetConfiguredModuleResponse(
        status="success",
        http_code=200,
        message="Module Fetched Successfully",
        module_id=module.id,
        module_type=module_type_name,
        device_id=device_uuid,
        slot_info=slot_info,
        category_info=category_info,
    )

