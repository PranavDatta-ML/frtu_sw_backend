import asyncio
import os
import subprocess
from typing import List
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
from src.schemas.frtu_modules import AddModuleManuallyRequest, DeviceModuleItem, DeviceModulesSimpleResponse
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


async def get_device_modules_simple(device_id: str, device_type: str) -> DeviceModulesSimpleResponse:
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
        raise HTTPException(status_code=400, detail="Device type does not match for this device_id")

    slots: List[FRTUSlots] = await FRTUSlots.select(device_id=device_uuid)
    if not slots:
        return DeviceModulesSimpleResponse(
            status="success",
            device_id=device_uuid,
            device_type=device_type,
            modules=[],
        )

    slot_ids = [s.id for s in slots]
    modules: List[FRTUModules] = await FRTUModules.select(slot_id=slot_ids)
    if not modules:
        return DeviceModulesSimpleResponse(
            status="success",
            device_id=device_uuid,
            device_type=device_type,
            modules=[],
        )

    module_type_ids = [m.module_type for m in modules]
    types = await FRTUModuleType.select(id=module_type_ids) if module_type_ids else []
    type_by_id = {t.id: t for t in types}

    items: List[DeviceModuleItem] = []
    for m in modules:
        t = type_by_id.get(m.module_type)
        type_name = t.name if t else None
        if not type_name:
            continue
        # find module_id from master by name if you need master id, else keep m.id
        masters = await FRTUModuleMaster.select(name=m.name)
        master_id = masters[0].id if masters else m.id

        items.append(
            DeviceModuleItem(
                slot_id=m.slot_id,
                module_id=master_id,
                module_type=type_name,
            )
        )

    return DeviceModulesSimpleResponse(
        satus_code = 200,
        status="success",
        device_id=device_uuid,
        device_type=device_type,
        modules=items,
    )
# ------------------- Configure Module Manually in Slot ----------------
import uuid
async def configure_module_manually(
    request: Request,
    frtu_name: str = Query(...),
    frtu_type: str = Query(...),
    authorization: str = Header(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return JSONResponse(status_code=401, content={"status": "error", "message": f"Tenant token decode failed: {str(e)}"})

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token: tenant_id missing"})

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"})

        payload = await request.json()
        module_name = payload.get("module_name")
        module_type = payload.get("module_type")
        # module_id = payload.get("module_id")
        slot_info = payload.get("slot_info", {})
        category_info = payload.get("category_info", {})

        if not module_name or not module_type or not slot_info:
            return JSONResponse(status_code=400, content={"status": "error", "message": "module_name, module_type, and slot_info are required"})

        slot_number = slot_info.get("slot_number")
        if not slot_number:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slot_number is required in slot_info"})

        try:
            slot_number = int(slot_number)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slot_number must be an integer"})

        if slot_number < 4 or slot_number > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only configure modules in slots 4-11"})

        if module_type not in ["DI", "DO"]:
            return JSONResponse(status_code=400, content={"status": "error", "message": "module_type must be 'DI' or 'DO'"})

        type_name_map = {
            "DO": "Digital Output",
            "DI": "Digital Input"
        }
        
        expected_name = type_name_map.get(module_type)
        if module_name != expected_name:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"module_name must be '{expected_name}' for type '{module_type}'"})

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found for this tenant"})

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found under tenant projects"})

        site_ids = [s.id for s in sites]
        devices = await FRTUDevices.select(name=frtu_name, type=frtu_type, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtu_name}' of type '{frtu_type}' not found for tenant"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slot_number > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slot_number} not found for device '{frtu_name}'"})

        slot = slots[slot_number - 1]
        
        existing_modules = await FRTUModules.select(slot_id=slot.id)
        if not existing_modules:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slot_number}. Please add module first."})

        module = existing_modules[0]
        current_attr = module.get("attribute", {}) or {}
        current_module_type = current_attr.get("module_type")

        if current_module_type != module_type:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Module type mismatch: slot {slot_number} has '{current_module_type}', but you provided '{module_type}'"})

        updated_attr = current_attr.copy()

        # if module_id:
            # updated_attr["module_id"] = module_id

        # updated_attr["module_name"] = current_attr.get("module_name", f"{slot.name}_{module_id or 'module'}")
        updated_attr["module_type"] = module_type
        updated_attr["slotnumber"] = slot_number

        if slot_info:
            current_slot_info = updated_attr.get("slot_info", {})
            updated_attr["slot_info"] = {**current_slot_info, **slot_info}

        if category_info:
            current_category_info = updated_attr.get("category_info", {})
            
            if module_type == "DI":
                total_channels = 16
                channel_prefix = "DI"
            else:
                total_channels = 10
                channel_prefix = "DO"
            
            if f"no_of_{module_type}_channel" not in current_category_info:
                current_category_info[f"total_no_of_{module_type}_channel"] = total_channels
                current_category_info["type"] = f"{total_channels} channel"
                current_category_info[f"no_of_{module_type}_channel"] = [
                    f"{channel_prefix}_{i}" for i in range(1, total_channels + 1)
                ]
            
            updated_attr["category_info"] = {**current_category_info, **category_info}

        naive_utc_now = datetime.utcnow()

        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            attribute=updated_attr,
            last_update_time=naive_utc_now
        )

        version_conf_synced = False
        version_conf_updates = {}
        
        if category_info and slot_number > 3:
            if "serial_number" in category_info:
                version_conf_updates["serial_number"] = category_info["serial_number"]
            if "hardware_version" in category_info:
                version_conf_updates["hardware_version"] = category_info["hardware_version"]
            if "software_version" in category_info:
                version_conf_updates["software_version"] = category_info["software_version"]
            
            if version_conf_updates:
                try:
                    update_version_conf(
                        slot_number=slot_number,
                        serial_number=version_conf_updates.get("serial_number"),
                        hardware_version=version_conf_updates.get("hardware_version"),
                        software_version=version_conf_updates.get("software_version")
                    )
                    version_conf_synced = True
                except Exception as e:
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "warning",
                            "message": f"Module configured in DB but failed to update version.conf: {str(e)}",
                            "updated_data": updated_attr
                        }
                    )

        response_data = {
            "status": "success",
            "message": f"Module in slot {slot_number} configured successfully",
            # "module_details": {
            #     "module_id": str(module["id"]),
            #     "module_name": updated_attr.get("module_name"),
            #     "module_type": module_type,
            #     "slot_number": slot_number,
            #     "attribute": updated_attr
            # }
        }
        
        # if version_conf_synced:
        #     response_data["version_conf_synced"] = True
        #     response_data["version_conf_updates"] = version_conf_updates

        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})







