import os
from fastapi import Query, Request, Header, Depends
from datetime import datetime, timezone
import uuid

from fastapi.responses import JSONResponse
from src.core.settings import Settings
from src.core.status_codes import HttpStatusCode
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_module_type import FRTUModuleType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.utils.access_token import decode_token
from src.utils.config_parser import parse_devids_conf, parse_version_conf, update_devids_conf, update_version_conf


# ------------------- Add Module Manually to Slot ----------------
async def add_module_manually(request: Request,frtu_name: str = Query(...),frtu_type: str = Query(...),authorization: str = Header(...),settings: Settings = Depends(Settings.get_settings)):
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

        tenant_id = uuid.UUID(tenant_id_str)

        payload = await request.json()
        module_name = payload.get("module_name")
        module_type = payload.get("module_type")
        slot_number = payload.get("slot_number")

        if not module_name or not module_type or not slot_number:
            return JSONResponse(status_code=400, content={"status": "error", "message": "module_name, module_type, and slot_number are required"})

        try:
            slot_number = int(slot_number)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "slot_number must be integer"})

        if slot_number < 4 or slot_number > 11:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Can only manually add modules to slots 4–11"})

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
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found for tenant"})
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No sites found under tenant projects"})
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtu_name, type=frtu_type, site_id=site_ids)
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtu_name}' of type '{frtu_type}' not found"})

        device = devices[0]
        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slot_number > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slot_number} not found for device '{frtu_name}'"})

        slot = slots[slot_number - 1]
        existing_modules = await FRTUModules.select(slot_id=slot.id)
        if existing_modules:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Slot {slot_number} already contains a module."})

        devids_data = parse_devids_conf()
        devids_slot_no = slot_number - 3 
        devids_entry = next((d for d in devids_data if int(d["slot_no"]) == devids_slot_no), None)

        if not devids_entry:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"No entry found in devids.conf for slot {slot_number}"})

        module_id = devids_entry.get("module_id", f"0x{devids_slot_no:02X}")  
        module_full_name = f"{slot.name}_{module_id}"

        try:
            version_data = parse_version_conf()
        except:
            version_data = {}

        version_info = version_data.get(devids_slot_no, {})

        if module_type == "DI":
            total_channels = 16
            card_type = "DI-16 Digital Input"
            channel_prefix = "DI"
        else:
            total_channels = 10
            card_type = "DO-10 Digital Output"
            channel_prefix = "DO"

        category_info = {}
        if version_info:
            category_info["serial_number"] = version_info.get("serial_number")
            category_info["hardware_version"] = version_info.get("hardware_version")
            category_info["software_version"] = version_info.get("software_version")

        category_info[f"total_no_of_{module_type}_channel"] = total_channels
        category_info["type"] = f"{total_channels} channel"
        category_info[f"no_of_{module_type}_channel"] = [
            f"{channel_prefix}_{i}" for i in range(1, total_channels + 1)
        ]

        attribute = {
            "slotnumber": slot_number,
            "module_name": module_full_name,
            "module_type": module_type,
            "module_id": module_id,
            "slot_info": {
                "slot_number": slot_number,
                "card_type": card_type
            },
            "category_info": category_info
        }

        module_type_objs = await FRTUModuleType.select(name=module_type)
        if module_type_objs:
            module_type_obj = module_type_objs[0]
        else:
            now = datetime.now()
            module_type_obj = await FRTUModuleType.insert(
                name=module_type,
                description=f"{module_type} module",
                attribute={},
                creation_time=now,
                last_update_time=now
            )

        now = datetime.now()
        new_module = await FRTUModules.insert(
            slot_id=slot.id,
            name=module_full_name,
            module_type=module_type_obj.id,
            description=f"{module_type} module",
            attribute=attribute,
            creation_time=now,
            last_update_time=now
        )

        try:
            update_devids_conf(slot_number, module_type)
        except Exception as e:
            await FRTUModules.delete(conditions={"id": new_module.id})
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to update devids.conf: {str(e)}. Rolled back."})

        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": f"{module_type} module added successfully to slot {slot_number}",
                "module_name": module_full_name,
                "module_id": module_id
            }
        )

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


# ------------------- Configure Module Manually in Slot ----------------
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







