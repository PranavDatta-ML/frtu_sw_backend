from datetime import datetime
import uuid, os
from uuid import UUID
from fastapi import Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from src.core.settings import Settings
from src.models.frtu_module_master import FRTUModuleMaster
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_modules import FRTUModules
from src.models.frtu_module_type import FRTUModuleType
from src import HttpStatusCode
import jwt # type: ignore
from src.config.auth_config import ALGORITHM, SECRET_KEY
from src.utils.access_token import decode_token
from src.utils.config_parser import parse_devids_conf, parse_version_conf


# ---------------- Auto Discover Modules if Device Exist and slot_info, categroy_info(attribute) ----------------
async def auto_discover_modules(
    request: Request,
    authorization: str = Header(..., convert_underscores=False),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return HttpStatusCode.UNAUTHORIZED.response(message=f"Tenant token decode failed: {str(e)}")

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(message="Invalid tenant token: tenant_id missing")

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

        project_records = await FRTUProjects.select(tenant_id=tenant_id)
        if not project_records:
            return HttpStatusCode.UNAUTHORIZED.response(message="No projects found for this tenant")

        payload = await request.json()
        entity = payload.get("entity", {})
        device_name = entity.get("name")
        device_type = entity.get("type")

        if not device_name or not device_type:
            return HttpStatusCode.BAD_REQUEST.response(message="Device name and type required")

        existing_devices = await FRTUDevices.select(name=device_name)
        if not existing_devices:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Device '{device_name}' does not exist. Please create device first."
            )

        device_obj = existing_devices[0]
        device_id = device_obj.id

        slots = await FRTUSlots.select(device_id=device_id)
        if not slots:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Device '{device_name}' has no slots. Please create slots first."
            )

        now = datetime.now()
        devids_data = parse_devids_conf()
        version_data = parse_version_conf()

        module_type_card_mapping = {
            "PS": "Power Supply",
            "COM": "Communication Module",
            "SOM": "SOM Module",
            "DI": "Digital Input",
            "DO": "Digital Output"
        }

        for idx, slot in enumerate(slots[:11], start=0):
            slot_number = idx + 1
            
            if idx < 3:
                module_type_name = ["PS", "COM", "SOM"][idx]
                module_name = f"{slot.name}_FIXED"
                module_id = str(uuid.uuid4())
                conf = None
                
                attribute = {
                    "slotnumber": slot_number,
                    "module_name": module_name,
                    "module_type": module_type_name,
                    "module_id": module_id,
                    "slot_info": {
                        "slot_number": slot_number,
                        "card_type": module_type_card_mapping[module_type_name]
                    },
                    "category_info": {
                        "description": module_type_name
                    }
                }
            else:
                conf = devids_data[idx - 3] if idx - 3 < len(devids_data) else None
                if not conf or conf["type_flag"] == 0:
                    continue
                
                module_type_name = "DI" if conf["type_flag"] == 1 else "DO"
                module_name = f"{slot.name}_{conf['module_id']}"
                module_id = conf['module_id']
                
                devids_slot_no = conf["slot_no"]
                version_info = version_data.get(devids_slot_no, {})
                
                if module_type_name == "DI":
                    total_channels = 16
                    card_type = "DI-16 Digital Input"
                    channel_prefix = "DI"
                elif module_type_name == "DO":
                    total_channels = 10
                    card_type = "DO-10 Digital Output"
                    channel_prefix = "DO"
                
                category_info = {}
                if version_info:
                    category_info["serial_number"] = version_info.get("serial_number")
                    category_info["hardware_version"] = version_info.get("hardware_version")
                    category_info["software_version"] = version_info.get("software_version")
                    category_info[f"total_no_of_{module_type_name}_channel"] = total_channels
                    category_info["type"] = f"{total_channels} channel"
                    category_info[f"no_of_{module_type_name}_channel"] = [
                        f"{channel_prefix}_{i}" for i in range(1, total_channels + 1)
                    ]
                
                attribute = {
                    "slotnumber": slot_number,
                    "module_name": module_name,
                    "module_type": module_type_name,
                    "module_id": module_id,
                    "slot_info": {
                        "slot_number": slot_number,
                        "card_type": card_type
                    },
                    "category_info": category_info
                }

            module_type_objs = await FRTUModuleType.select(name=module_type_name)
            if module_type_objs:
                module_type_obj = module_type_objs[0]
            else:
                module_type_obj = await FRTUModuleType.insert(
                    name=module_type_name,
                    description=f"{module_type_name} module",
                    attribute={},
                    creation_time=now,
                    last_update_time=now
                )

            existing_module = await FRTUModules.select(slot_id=slot.id, name=module_name)
            if existing_module:
                await FRTUModules.update(
                    conditions={"id": existing_module[0].id},
                    attribute=attribute,
                    last_update_time=now
                )
            else:
                await FRTUModules.insert(
                    slot_id=slot.id,
                    name=module_name,
                    module_type=module_type_obj.id,
                    description=f"{module_type_name} module",
                    attribute=attribute,
                    creation_time=now,
                    last_update_time=now
                )

        return HttpStatusCode.CREATED.response(
            message=f"Modules auto-discovered successfully for device '{device_name}'."
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# ---------------- Read Modules ----------------
async def get_auto_discover_modules(request: Request, name: str, type: str, authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}

    if not name or not type:
        return HttpStatusCode.BAD_REQUEST.response(message="Device name and type required")

    existing_devices = await FRTUDevices.select(name=name, type=type)
    if not existing_devices:
        return {
            "http_code": 404,
            "code": "NOT_FOUND",
            "message": f"Device with name '{name}' and type '{type}' not found."
        }

    device = existing_devices[0]
    device_id = device.id

    slots = await FRTUSlots.select(device_id=device_id)
    if not slots:
        return {
            "http_code": 404,
            "code": "NOT_FOUND",
            "message": f"No slots found for device '{name}'."
        }

    result_data = []
    for slot in slots:
        modules = await FRTUModules.select(slot_id=slot.id)
        module_data = []
        for mod in modules:
            mod_type_data = await FRTUModuleType.select(id=mod.module_type)
            mod_type_name = mod_type_data[0].name if mod_type_data else "Unknown"

            module_data.append({
                "module_name": mod.name,
                "module_type": mod_type_name,
                "description": mod.description,
                "creation_time": str(mod.creation_time),
                "last_update_time": str(mod.last_update_time)
            })

        result_data.append({
            "slot_name": slot.name,
            "slot_number": slot.slot_number if hasattr(slot, "slot_number") else None,
            "modules": module_data
        })

    response = {
        "http_code": 200,
        "code": "SUCCESS",
        "message": f"Auto-discovered module details for device '{name}'.",
        "data": {
            "device_name": name,
            "device_type": type,
            "slots": result_data
        }
    }

    return response


# -------------------------- Get Slot detail with modules detail ----------------------
async def get_auto_discover_modules_by_slot(request: Request, name: str, type: str, slotnumber: str, authorization: str = Header(...)):

    try:
        slotnumber_int = int(slotnumber)
    except ValueError:
        return {
            "http_code": 400,
            "code": "BAD_REQUEST",
            "message": f"Invalid slotnumber: {slotnumber}"
        }

    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}

    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": f"Tenant token decode failed: {str(e)}"}

    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "tenant_id missing in token"}

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

    projects = await FRTUProjects.select(tenant_id=tenant_id)
    if not projects:
        return {"http_code": 404, "code": "NOT_FOUND", "message": "No projects found for this tenant"}
    project_ids = [p.id for p in projects]

    sites = await FRTUSites.select(project_id=project_ids)
    if not sites:
        return {"http_code": 404, "code": "NOT_FOUND", "message": "No sites found under tenant projects"}
    site_ids = [s.id for s in sites]

    devices = await FRTUDevices.select(name=name, type=type, site_id=site_ids)
    if not devices:
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"Device '{name}' of type '{type}' not found for tenant"}
    device = devices[0]

    slots = await FRTUSlots.select(device_id=device.id)
    if not slots:
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"No slots found for device '{name}'"}

    if slotnumber_int < 1 or slotnumber_int > len(slots):
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"Slot {slotnumber_int} does not exist for device '{name}'"}
    
    slot = slots[slotnumber_int - 1]  

    modules = await FRTUModules.select(slot_id=slot.id)
    modules_data = []
    for m in modules:
        modules_data.append({
            "module_id": m.id,
            "name": m.name,
            "module_type": m.module_type,
            "description": m.description,
            "attribute": m.attribute,
            "creation_time": m.creation_time,
            "last_update_time": m.last_update_time
        })

    return {
        "http_code": 200,
        "code": "SUCCESS",
        "message": f"Slot {slotnumber_int} details fetched successfully",
        "data": {
            "device_name": device.name,
            "device_type": device.type,
            "slot_number": slotnumber_int,
            "slot_name": slot.name,
            "attribute": slot.attribute,
            "creation_time": slot.creation_time,
            "last_update_time": slot.last_update_time,
            "modules": modules_data
        }
    }


# ----------------------------- Update module detail using slot number incomplete------------------
async def update_auto_discover_modules(
    request: Request,
    name: str,
    type: str,
    slotnumber: str,
    authorization: str = Header(...)
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}

    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": f"Tenant token decode failed: {str(e)}"}

    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid tenant token: tenant_id missing"}
    tenant_id = uuid.UUID(tenant_id_str)

    projects = await FRTUProjects.select(tenant_id=tenant_id)
    if not projects:
        return {"http_code": 404, "code": "NOT_FOUND", "message": "No projects found for this tenant"}
    project_ids = [p.id for p in projects]

    sites = await FRTUSites.select(project_id=project_ids)
    if not sites:
        return {"http_code": 404, "code": "NOT_FOUND", "message": "No sites found under tenant projects"}
    site_ids = [s.id for s in sites]

    devices = await FRTUDevices.select(name=name, type=type, site_id=site_ids)
    if not devices:
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"Device '{name}' of type '{type}' not found"}
    device = devices[0]

    try:
        slot_idx = int(slotnumber) - 1
    except ValueError:
        return HttpStatusCode.BAD_REQUEST.response(message="Slotnumber must be an integer")

    slots = await FRTUSlots.select(device_id=device.id)
    if slot_idx < 0 or slot_idx >= len(slots):
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"Slot {slotnumber} not found for device '{name}'"}
    slot = slots[slot_idx]

    payload = await request.json()
    update_data = payload.get("update", {})
    if not update_data:
        return HttpStatusCode.BAD_REQUEST.response(message="No update data provided")

    modules = await FRTUModules.select(slot_id=slot.id)
    if not modules:
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"No modules found for slot {slotnumber}"}

    target_module_name = update_data.get("attribute", {}).get("module_name")
    module_to_update = None

    if target_module_name:
        for m in modules:
            if m.attribute and m.attribute.get("module_name") == target_module_name:
                module_to_update = m
                break
        if not module_to_update:
            return {"http_code": 404, "code": "NOT_FOUND", "message": f"Module '{target_module_name}' not found in slot {slotnumber}"}
    else:
        module_to_update = modules[0]

    fields_to_update = {}
    if "description" in update_data:
        fields_to_update["description"] = update_data["description"]

    if "attribute" in update_data:
        current_attr = module_to_update.attribute or {}
        fields_to_update["attribute"] = {**current_attr, **update_data["attribute"]}

    if fields_to_update:
        fields_to_update["last_update_time"] = datetime.now()
        await FRTUModules.update(module_to_update.id, **fields_to_update)

    return {
        "http_code": 200,
        "code": "SUCCESS",
        "message": f"Module '{module_to_update.name}' in slot {slotnumber} updated successfully",
        "updated_module": {
            "module_id": module_to_update.id,
            "name": module_to_update.name,
            "module_type": module_to_update.module_type,
            "slot_id": module_to_update.slot_id,
            **fields_to_update
        }
    }


# ---------------- Auto Discover Modules Message ----------------
async def auto_discover_modules_msg(
    request: Request,
    authorization: str = Header(..., convert_underscores=False),
    a_name: str = Query(...),
    a_type: str = Query(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return HttpStatusCode.UNAUTHORIZED.response(
                message=f"Tenant token decode failed: {str(e)}"
            )

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid tenant token: tenant_id missing"
            )

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Invalid tenant_id in token: {str(e)}"
            )

        frtu_name = a_name.strip()
        frtu_type = a_type.strip().upper()
        
        devices = await FRTUDevices.select(name=frtu_name, type=frtu_type)
        if not devices:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Device '{frtu_name}' with type '{frtu_type}' not found. Please create the device first."
            )
        device_obj = devices[0]

        site_records = await FRTUSites.select(id=device_obj.site_id)
        if not site_records:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Site for device '{frtu_name}' not found"
            )
        site_obj = site_records[0]

        project_records = await FRTUProjects.select(id=site_obj.project_id)
        if not project_records:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Project for site '{site_obj.name}' not found"
            )
        project_obj = project_records[0]

        if str(project_obj.tenant_id) != str(tenant_id):
            return HttpStatusCode.UNAUTHORIZED.response(
                message=f"Device '{frtu_name}' does not belong to tenant"
            )

        slots = await FRTUSlots.select(device_id=device_obj.id)
        if not slots:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No slots found for device '{frtu_name}'. Please create slots first."
            )
        
        slots.sort(key=lambda x: x.name)
        
        try:
            devids_data = parse_devids_conf()
        except FileNotFoundError as e:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Configuration file not found: {str(e)}"
            )

        now = datetime.now()
        
        for idx in range(4, 12):
            devids_index = idx - 3
            
            if idx - 1 >= len(slots):
                continue
                
            slot = slots[idx - 1]
            
            conf = next((c for c in devids_data if int(c.get("slot_no", -1)) == devids_index),None
            )
            
            existing_modules = await FRTUModules.select(slot_id=slot.id)
            
            if conf:
                type_flag = int(conf.get("type_flag", 0))
                
                if type_flag == 0:
                    for module in existing_modules:
                        module_type_objs = await FRTUModuleType.select(id=module.module_type)
                        if module_type_objs:
                            module_type_name = module_type_objs[0].name.upper()
                            if module_type_name in ["DI", "DO"]:
                                await FRTUModules.delete(conditions={"id": module.id})
                
                elif type_flag in [1, 2]:
                    module_type_name = "DI" if type_flag == 1 else "DO"
                    module_name = f"{slot.name}_{conf['module_id']}"
                    
                    module_type_objs = await FRTUModuleType.select(name=module_type_name)
                    if module_type_objs:
                        module_type_obj = module_type_objs[0]
                    else:
                        module_type_obj = await FRTUModuleType.insert(
                            name=module_type_name,
                            description=f"{module_type_name} module",
                            attribute={},
                            creation_time=now,
                            last_update_time=now
                        )
                    
                    existing_di_do_modules = []
                    for existing_module in existing_modules:
                        existing_type_objs = await FRTUModuleType.select(id=existing_module.module_type)
                        if existing_type_objs and existing_type_objs[0].name in ["DI", "DO"]:
                            existing_di_do_modules.append(existing_module)
                    
                    if existing_di_do_modules:
                        target_module = existing_di_do_modules[0]
                        current_type_objs = await FRTUModuleType.select(id=target_module.module_type)
                        current_type_name = current_type_objs[0].name if current_type_objs else None
                        
                        if current_type_name != module_type_name:
                            await FRTUModules.update(
                                conditions={"id": target_module.id},
                                name=module_name,
                                module_type=module_type_obj.id,
                                description=f"{module_type_name} module",
                                last_update_time=now
                            )
                        
                        for extra_module in existing_di_do_modules[1:]:
                            await FRTUModules.delete(conditions={"id": extra_module.id})
                    else:
                        await FRTUModules.insert(
                            slot_id=slot.id,
                            name=module_name,
                            module_type=module_type_obj.id,
                            description=f"{module_type_name} module",
                            creation_time=now,
                            last_update_time=now
                        )
            else:
                for module in existing_modules:
                    module_type_objs = await FRTUModuleType.select(id=module.module_type)
                    if module_type_objs:
                        module_type_name = module_type_objs[0].name.upper()
                        if module_type_name in ["DI", "DO"]:
                            await FRTUModules.delete(conditions={"id": module.id})

        slots = await FRTUSlots.select(device_id=device_obj.id)
        slots.sort(key=lambda x: x.name)
        
        total_slots = 11
        
        di_slots = []
        do_slots = []
        power_slot = "1"
        comm_slot = "2"
        som_slot = "3"

        for idx in range(1, 4):
            if idx - 1 < len(slots):
                slot = slots[idx - 1]
                module_records = await FRTUModules.select(slot_id=slot.id)
                
                if module_records:
                    for module in module_records:
                        module_type_objs = await FRTUModuleType.select(id=module.module_type)
                        if module_type_objs:
                            module_type_name = module_type_objs[0].name.upper()
                            if module_type_name == "PS":
                                power_slot = str(idx)
                            elif module_type_name == "COM":
                                comm_slot = str(idx)
                            elif module_type_name == "SOM":
                                som_slot = str(idx)

        for idx in range(4, 12):
            if idx - 1 < len(slots):
                slot = slots[idx - 1]
                module_records = await FRTUModules.select(slot_id=slot.id)
                
                if module_records:
                    for module in module_records:
                        module_type_objs = await FRTUModuleType.select(id=module.module_type)
                        
                        if module_type_objs:
                            module_type_name = module_type_objs[0].name.upper()
                            
                            if module_type_name == "DI":
                                di_slots.append(str(idx))
                            elif module_type_name == "DO":
                                do_slots.append(str(idx))

        if not di_slots and not do_slots:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No DI/DO modules found for device '{frtu_name}'. Check devids.conf configuration."
            )

        filled_di_do_slots = len(di_slots) + len(do_slots)
        empty_di_do_slots = 8 - filled_di_do_slots

        modules_message = {
            "Power Supply Identified in Slot": power_slot,
            "Communication Module Identified in Slot": comm_slot,
            "SOM Module Identified in Slot": som_slot
        }
        
        if di_slots:
            modules_message["DI Module Identified in Slots"] = " / ".join(di_slots)
        
        if do_slots:
            modules_message["DO Module Identified in Slots"] = " / ".join(do_slots)

        result = {
            "frtuName": frtu_name,
            "frtuType": frtu_type,
            "totalSlots": str(total_slots),
            "emptySlots": str(empty_di_do_slots),
            "totalDI": str(len(di_slots)),
            "totalDO": str(len(do_slots)),
            "modules": modules_message
        }

        return HttpStatusCode.OK.response(
            message=f"Auto-discovery summary for {frtu_name} (synced with devids.conf)",
            data=result
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Error processing request: {str(e)}"
        )


# ---------------- Auto Discover Modules List ----------------
async def auto_discover_modules_list(
    request: Request,
    authorization: str = Header(..., convert_underscores=False),
    a_name: str = Query(...),
    a_type: str = Query(...),
    settings: Settings = Depends(Settings.get_settings)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid Authorization header"
            )

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return HttpStatusCode.UNAUTHORIZED.response(
                message=f"Tenant token decode failed: {str(e)}"
            )

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return HttpStatusCode.UNAUTHORIZED.response(
                message="Invalid tenant token: tenant_id missing"
            )

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Invalid tenant_id in token: {str(e)}"
            )

        frtu_name = a_name.strip()
        frtu_type = a_type.strip().upper()
        
        devices = await FRTUDevices.select(name=frtu_name, type=frtu_type)
        if not devices:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Device '{frtu_name}' with type '{frtu_type}' not found. Please create the device first."
            )
        device_obj = devices[0]

        site_records = await FRTUSites.select(id=device_obj.site_id)
        if not site_records:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Site for device '{frtu_name}' not found"
            )
        site_obj = site_records[0]

        project_records = await FRTUProjects.select(id=site_obj.project_id)
        if not project_records:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Project for site '{site_obj.name}' not found"
            )
        project_obj = project_records[0]

        if str(project_obj.tenant_id) != str(tenant_id):
            return HttpStatusCode.UNAUTHORIZED.response(
                message=f"Device '{frtu_name}' does not belong to tenant"
            )

        slots = await FRTUSlots.select(device_id=device_obj.id)
        if not slots:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No slots found for device '{frtu_name}'. Please create slots first."
            )
        
        slots.sort(key=lambda x: x.name)
        
        try:
            devids_data = parse_devids_conf()
        except FileNotFoundError as e:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Configuration file not found: {str(e)}"
            )

        now = datetime.now()
        
        for idx in range(4, 12):
            devids_index = idx - 3
            
            if idx - 1 >= len(slots):
                continue
                
            slot = slots[idx - 1]
            
            conf = next(
                (c for c in devids_data if int(c.get("slot_no", -1)) == devids_index),
                None
            )
            
            existing_modules = await FRTUModules.select(slot_id=slot.id)
            
            if conf:
                type_flag = int(conf.get("type_flag", 0))
                
                if type_flag == 0:
                    for module in existing_modules:
                        module_type_objs = await FRTUModuleType.select(id=module.module_type)
                        if module_type_objs:
                            module_type_name = module_type_objs[0].name.upper()
                            if module_type_name in ["DI", "DO"]:
                                await FRTUModules.delete(conditions={"id": module.id})
                
                elif type_flag in [1, 2]:
                    module_type_name = "DI" if type_flag == 1 else "DO"
                    module_name = f"{slot.name}_{conf['module_id']}"
                    
                    module_type_objs = await FRTUModuleType.select(name=module_type_name)
                    if module_type_objs:
                        module_type_obj = module_type_objs[0]
                    else:
                        module_type_obj = await FRTUModuleType.insert(
                            name=module_type_name,
                            description=f"{module_type_name} module",
                            attribute={},
                            creation_time=now,
                            last_update_time=now
                        )
                    
                    existing_di_do_modules = []
                    for existing_module in existing_modules:
                        existing_type_objs = await FRTUModuleType.select(id=existing_module.module_type)
                        if existing_type_objs and existing_type_objs[0].name in ["DI", "DO"]:
                            existing_di_do_modules.append(existing_module)
                    
                    if existing_di_do_modules:
                        target_module = existing_di_do_modules[0]
                        current_type_objs = await FRTUModuleType.select(id=target_module.module_type)
                        current_type_name = current_type_objs[0].name if current_type_objs else None
                        
                        if current_type_name != module_type_name:
                            await FRTUModules.update(
                                conditions={"id": target_module.id},
                                name=module_name,
                                module_type=module_type_obj.id,
                                description=f"{module_type_name} module",
                                last_update_time=now
                            )
                        
                        for extra_module in existing_di_do_modules[1:]:
                            await FRTUModules.delete(conditions={"id": extra_module.id})
                    else:
                        await FRTUModules.insert(
                            slot_id=slot.id,
                            name=module_name,
                            module_type=module_type_obj.id,
                            description=f"{module_type_name} module",
                            creation_time=now,
                            last_update_time=now
                        )
            else:
                for module in existing_modules:
                    module_type_objs = await FRTUModuleType.select(id=module.module_type)
                    if module_type_objs:
                        module_type_name = module_type_objs[0].name.upper()
                        if module_type_name in ["DI", "DO"]:
                            await FRTUModules.delete(conditions={"id": module.id})

        slots = await FRTUSlots.select(device_id=device_obj.id)
        slots.sort(key=lambda x: x.name)
        
        total_slots = 11
        module_type_mapping = {
            "PS": "Power Supply",
            "COM": "Communication Module",
            "SOM": "SOM Module",
            "DI": "Digital Input",
            "DO": "Digital Output"
        }
        
        modules_list = []
        di_count = 0
        do_count = 0

        for idx in range(1, total_slots + 1):
            if idx - 1 < len(slots):
                slot = slots[idx - 1]
                module_records = await FRTUModules.select(slot_id=slot.id)
                
                if module_records:
                    for module in module_records:
                        module_type_objs = await FRTUModuleType.select(id=module.module_type)
                        
                        if module_type_objs:
                            module_type_name = module_type_objs[0].name.upper()
                            
                            if module_type_name in module_type_mapping:
                                display_name = module_type_mapping[module_type_name]
                                modules_list.append(f"{display_name} ({idx})")
                                
                                if module_type_name == "DI":
                                    di_count += 1
                                elif module_type_name == "DO":
                                    do_count += 1

        if not modules_list:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No modules found for device '{frtu_name}'. Check devids.conf configuration."
            )

        filled_di_do_slots = di_count + do_count
        empty_di_do_slots = 8 - filled_di_do_slots

        result = {
            "frtuName": frtu_name,
            "frtuType": frtu_type,
            "totalSlots": str(total_slots),
            "emptySlots": str(empty_di_do_slots),
            "totalDI": str(di_count),
            "totalDO": str(do_count),
            "modules": modules_list
        }

        return HttpStatusCode.OK.response(
            message=f"Auto-discovery module list for {frtu_name}",
            data=result
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Error processing request: {str(e)}"
        )


# ---------------------- Manual Auto Discover Module List -----------------
async def get_module_list(request: Request, authorization: str = Header(...)):
    try:
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        token = authorization.split(" ")[1]
        tenant_data = decode_token(token)
        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "tenant_id missing in token"})
        tenant_id = uuid.UUID(tenant_id_str)

        modules = await FRTUModuleMaster.select(columns=[FRTUModuleMaster.name])

        # Flatten to list of strings
        module_list = [m["name"] for m in modules]

        return JSONResponse(status_code=200, content={"status": "success", "modules": module_list})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})




# ---------------- Auto Discover Modules Device Exist ----------------
# async def auto_discover_modules(
#     request: Request,
#     authorization: str = Header(..., convert_underscores=False),
#     settings: Settings = Depends(Settings.get_settings)
# ):
#     try:
#         # --- Validate Authorization ---
#         if not authorization or not authorization.startswith("Bearer "):
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

#         tenant_token = authorization.split(" ")[1]
#         try:
#             tenant_data = decode_token(tenant_token)
#         except Exception as e:
#             return HttpStatusCode.UNAUTHORIZED.response(message=f"Tenant token decode failed: {str(e)}")

#         tenant_id_str = tenant_data.get("tenant_id")
#         if not tenant_id_str:
#             return HttpStatusCode.UNAUTHORIZED.response(message="Invalid tenant token: tenant_id missing")

#         try:
#             tenant_id = uuid.UUID(tenant_id_str)
#         except Exception as e:
#             return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

#         # --- Validate Tenant Exists in Projects ---
#         project_records = await FRTUProjects.select(tenant_id=tenant_id)
#         if not project_records:
#             return HttpStatusCode.UNAUTHORIZED.response(message="No projects found for this tenant")

#         # --- Parse Request Payload ---
#         payload = await request.json()
#         entity = payload.get("entity", {})
#         device_name = entity.get("name")
#         device_type = entity.get("type")

#         if not device_name or not device_type:
#             return HttpStatusCode.BAD_REQUEST.response(message="Device name and type required")

#         # --- Check if Device Exists ---
#         existing_devices = await FRTUDevices.select(name=device_name)
#         if not existing_devices:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Device '{device_name}' does not exist. Please create device first."
#             )

#         device_obj = existing_devices[0]
#         device_id = device_obj.id

#         # --- Get Slots for the Device ---
#         slots = await FRTUSlots.select(device_id=device_id)
#         if not slots:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Device '{device_name}' has no slots. Please create slots first."
#             )

#         now = datetime.now()
#         devids_data = parse_devids_conf()

#         # --- Map Slots to Modules Based on devids.conf ---
#         for idx, slot in enumerate(slots[:11], start=0):
#             if idx < 3:
#                 module_type_name = ["PS", "COM", "SOM"][idx]
#                 module_name = f"{slot.name}_FIXED"
#             else:
#                 conf = devids_data[idx - 3] if idx - 3 < len(devids_data) else None
#                 if not conf or conf["type_flag"] == 0:
#                     continue
#                 module_type_name = "DI" if conf["type_flag"] == 1 else "DO"
#                 module_name = f"{slot.name}_{conf['module_id']}"

#             # --- Module Type (Insert if not exists) ---
#             module_type_objs = await FRTUModuleType.select(name=module_type_name)
#             if module_type_objs:
#                 module_type_obj = module_type_objs[0]
#             else:
#                 module_type_obj = await FRTUModuleType.insert(
#                     name=module_type_name,
#                     description=f"{module_type_name} module",
#                     attribute={},
#                     creation_time=now,
#                     last_update_time=now
#                 )

#             # --- Module (Insert if not exists) ---
#             existing_module = await FRTUModules.select(slot_id=slot.id, name=module_name)
#             if existing_module:
#                 continue

#             await FRTUModules.insert(
#                 slot_id=slot.id,
#                 name=module_name,
#                 module_type=module_type_obj.id,
#                 description=f"{module_type_name} module",
#                 creation_time=now,
#                 last_update_time=now
#             )

#         return HttpStatusCode.CREATED.response(
#             message=f"Modules auto-discovered successfully for device '{device_name}'."
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))



