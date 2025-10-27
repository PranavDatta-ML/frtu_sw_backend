import os
from fastapi import Query, Request, Header, Depends
from datetime import datetime, timezone
import uuid

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
from src.utils.access_token import decode_token
from src.utils.config_parser import parse_version_conf, update_version_conf

# ---------------- Get Slot Module Detail ----------------
async def get_slot_module_detail(request: Request,frtuname: str,frtutype: str,slotnumber: str,authorization: str = Header(...),settings: Settings = Depends(Settings.get_settings)):
    try:
        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return {"status": "error", "message": "Invalid slotnumber: must be an integer"}

        if not authorization or not authorization.startswith("Bearer "):
            return {"status": "error", "message": "Invalid Authorization header"}

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return {"status": "error", "message": f"Tenant token decode failed: {str(e)}"}

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return {"status": "error", "message": "Invalid tenant token: tenant_id missing"}

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return {"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"}

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return {"status": "error", "message": "No projects found for this tenant"}

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return {"status": "error", "message": "No sites found under tenant projects"}

        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return {"status": "error", "message": f"Device '{frtuname}' of type '{frtutype}' not found for tenant"}

        device = devices[0]

        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber < 1 or slotnumber > len(slots):
            return {"status": "error", "message": f"Slot {slotnumber} not found for device '{frtuname}'"}

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot.id)
        if not modules:
            return {"status": "error", "message": f"No module found in slot {slotnumber} for device '{frtuname}'"}

        module = modules[0]

        attr = module.attribute or {}
        response_data = {
            "status": "success",
            "slotnumber": slotnumber,
            "module_name": attr.get("module_name", module.name),
            "module_type": attr.get("module_type", "Unknown"),
            "module_id": attr.get("module_id", ""),
            "slot_info": attr.get("slot_info", {}),
            "category_info": attr.get("category_info", {})
        }

        return response_data

    except Exception as e:
        return {"status": "error", "message": f"Error fetching slot details: {str(e)}"}


# ------------------ Get Available Slot ---------------- 
async def get_available_slots(request: Request,authorization: str = Header(...),settings: Settings = Depends(Settings.get_settings)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return {"status": "error", "message": "Invalid Authorization header"}

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return {"status": "error", "message": f"Tenant token decode failed: {str(e)}"}

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return {"status": "error", "message": "Invalid tenant token: tenant_id missing"}

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return {"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"}

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return {"status": "error", "message": "No projects found for this tenant"}

        project_ids = [p.id for p in projects]
        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return {"status": "error", "message": "No sites found under tenant projects"}

        site_ids = [s.id for s in sites]
        devices = await FRTUDevices.select(site_id=site_ids)
        if not devices:
            return {"status": "error", "message": "No devices found for this tenant"}

        all_available_slots = []

        for device in devices:
            slots = await FRTUSlots.select(device_id=device.id)
            for slot in slots:
                modules = await FRTUModules.select(slot_id=slot.id)
                if not modules:  
                    try:
                        slot_attr = slot.attribute or {}
                        slot_no = slot_attr.get("slot_number")
                        if slot_no is None:
                            slot_no = int(slot.name.split("_")[-1]) if "_" in slot.name else None
                        if slot_no:
                            all_available_slots.append(slot_no)
                    except Exception:
                        continue

        if not all_available_slots:
            return {"status": "success", "available_slot_number": [], "message": "No available slots found."}

        all_available_slots = sorted(list(set(all_available_slots)))
        return {
            "status": "success",
            "available_slot_number": all_available_slots,
            "message": f"{len(all_available_slots)} available slots found."
        }

    except Exception as e:
        return {"status": "error", "message": f"Error fetching available slots: {str(e)}"}


#  ------------------- Get Module Category type Options ----------------
async def get_slot_module_options(request: Request,frtuname: str = Query(...),frtutype: str = Query(...),slotnumber: int = Query(...),authorization: str = Header(..., convert_underscores=False),settings: Settings = Depends(Settings.get_settings)):
    try:
        slotnumber = int(slotnumber)
        if not authorization or not authorization.startswith("Bearer "):
            return {"status": "error", "message": "Invalid Authorization header"}

        tenant_token = authorization.split(" ")[1]
        try:
            tenant_data = decode_token(tenant_token)
        except Exception as e:
            return {"status": "error", "message": f"Tenant token decode failed: {str(e)}"}

        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return {"status": "error", "message": "Invalid tenant token: tenant_id missing"}

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except Exception as e:
            return {"status": "error", "message": f"Invalid tenant_id in token: {str(e)}"}

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return {"status": "error", "message": "No projects found for this tenant"}
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return {"status": "error", "message": "No sites found for this tenant"}
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(name=frtuname, type=frtutype, site_id=site_ids)
        if not devices:
            return {"status": "error", "message": f"Device '{frtuname}' of type '{frtutype}' not found for this tenant"}
        device = devices[0]

        slots = await FRTUSlots.select(device_id=device.id)
        if not slots or slotnumber < 1 or slotnumber > len(slots):
            return {"status": "error", "message": f"Invalid slot number {slotnumber} for device '{frtuname}'"}

        slot = slots[slotnumber - 1]

        if slotnumber == 1:
            module_type = "PS"
        elif slotnumber == 2:
            module_type = "COM"
        elif slotnumber == 3:
            module_type = "SOM"
        else:
            modules = await FRTUModules.select(slot_id=slot.id)
            if modules and modules[0].attribute:
                module_type = modules[0].attribute.get("module_type", "UNKNOWN")
            else:
                module_type = "UNKNOWN"

        module_mapping = {
            "PS": {
                "card_type": "Power Supply",
                "type": ["48V DC", "24V DC", "110V DC", "220V DC", "230V DC", "110V AC"]
            },
            "COM": {
                "card_type": "Communication Module",
                "type": ["Processor 1", "Processor 2", "Processor 3"]
            },
            "SOM": {
                "card_type": "SOM Module",
                "type": ["Processor 1", "Processor 2", "Processor 3"]
            },
            "DI": {
                "card_type": "DI-16 Digital Input",
                "type": ["16 channel", "8 channel", "24 channel"]
            },
            "DO": {
                "card_type": "DO-10 Digital Output",
                "type": ["8 channel", "10 channel"]
            }
        }

        if module_type not in module_mapping:
            return {"status": "error", "message": f"No predefined module options for slot {slotnumber} (type: {module_type})"}

        module_data = module_mapping[module_type]

        return {
            "status": "success",
            "slotnumber": slotnumber,
            "module_type": module_type,
            "slot_info": {
                "card_type": module_data["card_type"]
            },
            "category_info": {
                "type": module_data["type"]
            }
        }

    except Exception as e:
        return {"status": "error", "message": f"Error fetching slot module options: {str(e)}"}


# ------------------- Get Module Card types options ----------------
async def get_card_type(request: Request, authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Invalid Authorization header"}
        )
    
    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": f"Tenant token decode failed: {str(e)}"}
        )
    
    tenant_id = tenant_data.get("tenant_id")
    if not tenant_id:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "tenant_id missing in token"}
        )

    card_types = [
        "Power Supply",
        "Slave Processor",
        "Communication 1 : Ethernet",
        "Communication 2 : OFC, Time Sync",
        "Communication 3 : Modbus",
        "DI-16 Digital Input",
        "DO-10 Digital Output",
        "AI-10 Analog Input",
        "AO-8 Analog Output"
    ]
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "card_types": card_types
        }
    )


# ------------------- Update Module Detail by slotnumber ----------------
async def update_module_detail(
    request: Request,
    frtu_name: str,
    frtu_type: str,
    slotnumber: str,
    authorization: str = Header(...),
):
    try:
        try:
            slotnumber = int(slotnumber)
        except ValueError:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid slotnumber: must be integer"})

        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid Authorization header"})

        tenant_token = authorization.split(" ")[1]
        tenant_data = decode_token(tenant_token)
        tenant_id_str = tenant_data.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid tenant token: tenant_id missing"})
        tenant_id = uuid.UUID(tenant_id_str)

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return JSONResponse(status_code=404, content={"status": "error", "message": "No projects found"})

        sites = await FRTUSites.select(project_id=[p["id"] for p in projects])
        devices = await FRTUDevices.select(name=frtu_name, type=frtu_type, site_id=[s["id"] for s in sites])
        if not devices:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Device '{frtu_name}' of type '{frtu_type}' not found"})

        slots = await FRTUSlots.select(device_id=devices[0]["id"])
        if not slots or slotnumber < 1 or slotnumber > len(slots):
            return JSONResponse(status_code=404, content={"status": "error", "message": f"Slot {slotnumber} not found"})

        slot = slots[slotnumber - 1]
        modules = await FRTUModules.select(slot_id=slot["id"])
        if not modules or modules[0] is None:
            return JSONResponse(status_code=404, content={"status": "error", "message": f"No module found in slot {slotnumber}"})

        module = modules[0]
        attr = module.get("attribute", {}) or {}

        existing_type = attr.get("module_type", "Unknown")
        type_name_map = {
            "DO": "Digital Output",
            "DI": "Digital Input",
            "PS": "Power Supply",
            "SOM": "SOM Module",
            "COM": "Communication Module",
        }
        expected_name = type_name_map.get(existing_type, attr.get("module_name"))

        payload = await request.json()
        module_name = payload.get("module_name")
        module_type = payload.get("module_type")

        if module_type and module_type != existing_type:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Module type mismatch: expected '{existing_type}', got '{module_type}'"})

        if module_name and module_name != expected_name:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Module name mismatch for type '{module_type}': expected '{expected_name}', got '{module_name}'"})

        updated_attr = attr.copy()
        
        version_conf_updates = {}
        db_updates = {}
        
        for key, value in payload.items():
            if key in ["module_name", "module_type"]:
                continue
            
            if key == "description":
                db_updates["description"] = value
                continue
            
            if isinstance(value, dict):
                updated_attr[key] = {**updated_attr.get(key, {}), **value}
                
                if key == "category_info" and slotnumber > 3:
                    if "serial_number" in value:
                        version_conf_updates["serial_number"] = value["serial_number"]
                    if "hardware_version" in value:
                        version_conf_updates["hardware_version"] = value["hardware_version"]
                    if "software_version" in value:
                        version_conf_updates["software_version"] = value["software_version"]
            else:
                updated_attr[key] = value

        updated_attr["module_name"] = expected_name
        updated_attr["module_type"] = existing_type

        naive_utc_now = datetime.utcnow()
        
        db_updates["attribute"] = updated_attr
        db_updates["last_update_time"] = naive_utc_now

        await FRTUModules.update(
            extra={},
            conditions={"id": module["id"]},
            **db_updates
        )

        version_conf_synced = False
        if version_conf_updates and slotnumber > 3:
            try:
                update_version_conf(
                    slot_number=slotnumber,
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
                        "message": f"Module updated in DB but failed to update version.conf: {str(e)}",
                        "updated_data": updated_attr,
                    }
                )

        response_data = {
            "status": "success",
            "message": f"Module updated successfully!"
        }
        
        # if "description" in db_updates:
        #     response_data["description_updated"] = True
        #     response_data["new_description"] = db_updates["description"]
        
        # if version_conf_synced:
        #     response_data["version_conf_synced"] = True
        #     response_data["version_conf_updates"] = version_conf_updates

        return JSONResponse(status_code=200, content=response_data)

    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})




