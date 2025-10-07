from datetime import datetime
import uuid, os
from uuid import UUID
from fastapi import Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from src.core.settings import Settings
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_modules import FRTUModules
from src.models.frtu_module_type import FRTUModuleType
from src import HttpStatusCode
import jwt
from src.config.auth_config import ALGORITHM, SECRET_KEY
from src.views.frtu_devices import create_device, read_devices

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVIDS_CONF_PATH = os.path.join(BASE_DIR, "config", "devids.conf")

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def parse_devids_conf():
    if not os.path.exists(DEVIDS_CONF_PATH):
        raise FileNotFoundError(f"devids.conf not found at {DEVIDS_CONF_PATH}")

    modules = []
    with open(DEVIDS_CONF_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            parts = line.split()
            if len(parts) >= 5:
                modules.append({
                    "slot_no": int(parts[0]),
                    "dev_path": parts[1],
                    "module_id": parts[2],
                    "gpino": parts[3],
                    "type_flag": int(parts[4])  
                })
    return modules

# ---------------- Auto Discover Modules Device Exist ----------------
async def auto_discover_modules(request: Request, authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}

    payload = await request.json()
    entity = payload.get("entity", {})
    device_name = entity.get("name")
    device_type = entity.get("type")

    if not device_name or not device_type:
        return HttpStatusCode.BAD_REQUEST.response(message="Device name and type required")

    existing_devices = await FRTUDevices.select(name=device_name)
    if not existing_devices:
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"Device '{device_name}' does not exist. Please create device first."}

    device_obj = existing_devices[0]
    device_id = device_obj.id
    slots = await FRTUSlots.select(device_id=device_id)
    if not slots:
        return {"http_code": 404, "code": "NOT_FOUND", "message": f"Device '{device_name}' has no slots. Please create slots first."}

    now = datetime.now()
    devids_data = parse_devids_conf()
    for idx, slot in enumerate(slots[:11], start=0):
        if idx < 3:
            module_type_name = ["PS", "COM", "SOM"][idx]
            module_name = f"{slot.name}_FIXED"
        else:
            conf = devids_data[idx - 3] if idx - 3 < len(devids_data) else None
            if not conf or conf["type_flag"] == 0:
                continue
            module_type_name = "DI" if conf["type_flag"] == 1 else "DO"
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

        existing_module = await FRTUModules.select(slot_id=slot.id, name=module_name)
        if existing_module:
            continue 

        await FRTUModules.insert(
            slot_id=slot.id,
            name=module_name,
            module_type=module_type_obj.id,
            description=f"{module_type_name} module",
            creation_time=now,
            last_update_time=now
        )

    return {"http_code": 201, "code": "CREATED", "message": f"Modules auto-discovered successfully for device '{device_name}'."}


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
# async def auto_discover_modules_msg(
#     request: Request,
#     authorization: str = Header(..., convert_underscores=False),
#     a_name: str = Query(...),
#     a_type: str = Query(...),
#     settings: Settings = Depends(Settings.get_settings)
# ):
#     try:
#         # ---------------- Authorization ----------------
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

#         # ---------------- Input ----------------
#         frtu_name = a_name.strip()
#         frtu_type = a_type.strip().upper()
#         now = datetime.now().replace(tzinfo=None)

#         # ---------------- Device ----------------
#         devices = await FRTUDevices.select(name=frtu_name)
#         if not devices:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Device '{frtu_name}' not found in DB"
#             )
#         device_obj = devices[0]

#         # ---------------- Site + Project + Tenant Validation ----------------
#         site_records = await FRTUSites.select(id=device_obj.site_id)
#         if not site_records:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Site for device '{frtu_name}' not found"
#             )
#         site_obj = site_records[0]

#         project_records = await FRTUProjects.select(id=site_obj.project_id)
#         if not project_records:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Project for site '{site_obj.name}' not found"
#             )
#         project_obj = project_records[0]

#         if str(project_obj.tenant_id) != str(tenant_id):
#             return HttpStatusCode.UNAUTHORIZED.response(
#                 message=f"Device '{frtu_name}' does not belong to tenant"
#             )

#         # ---------------- Slots ----------------
#         slots = await FRTUSlots.select(device_id=device_obj.id)
#         if not slots:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"No slots found for device '{frtu_name}'"
#             )
#         slots.sort(key=lambda x: x.name)

#         total_slots = 11
#         total_di = 0
#         total_do = 0
#         empty_slots = []
#         di_slots = []
#         do_slots = []
#         modules_summary = {}

#         # ---------------- Fixed Slots ----------------
#         modules_summary["Power Supply Identified in Slot"] = "1"
#         modules_summary["Communication Module Identified in Slot"] = "2"
#         modules_summary["SOM Module Identified in Slot"] = "3"

#         devids_data = parse_devids_conf()

#         # ---------------- Module Discovery ----------------
#         for idx, slot in enumerate(slots, start=1):
#             if idx <= 3:
#                 continue  # Skip first three fixed modules

#             module_records = await FRTUModules.select(slot_id=slot.id)

#             if module_records:
#                 module_type_id = module_records[0]["module_type"]
#                 module_type_data = await FRTUModuleType.select(id=module_type_id)
#                 module_type_name = (
#                     module_type_data[0]["name"] if module_type_data else "UNKNOWN"
#                 )
#             else:
#                 # Match regardless of whether slot_no is str or int
#                 conf = next(
#                     (
#                         c for c in devids_data
#                         if str(c.get("slot_no")) == str(idx)
#                     ),
#                     None,
#                 )

#                 # Mark empty slot if not found or type_flag=0
#                 if not conf or int(conf.get("type_flag", 0)) == 0:
#                     empty_slots.append(str(idx))
#                     continue

#                 module_type_name = "DI" if conf["type_flag"] == 1 else "DO"

#             # Count DI/DO slots
#             if module_type_name == "DI":
#                 total_di += 1
#                 di_slots.append(str(idx))
#             elif module_type_name == "DO":
#                 total_do += 1
#                 do_slots.append(str(idx))
#             else:
#                 empty_slots.append(str(idx))


#         # ---------------- Summary ----------------
#         if di_slots:
#             modules_summary["DI Module Identified in Slots"] = " / ".join(di_slots)
#         if do_slots:
#             modules_summary["DO Module Identified in Slots"] = " / ".join(do_slots)

#         # ---------------- Result ----------------
#         result = {
#             "frtuName": frtu_name,
#             "frtuType": frtu_type,
#             "totalSlots": total_slots,
#             "emptySlots": str(len(empty_slots)),
#             "totalDI": str(total_di),
#             "totalDO": str(total_do),
#             "modules": modules_summary
#         }

#         return HttpStatusCode.OK.response(
#             message=f"Auto-discovery summary for {frtu_name}",
#             data=result
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))




# # ---------------- Auto Discover Modules device not exist create device, slots ----------------
# # async def auto_discover_modules(request: Request, authorization: str = Header(...)):
#     if not authorization or not authorization.startswith("Bearer "):
#         return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}
    
#     tenant_token = authorization.split(" ")[1]
#     tenant_data = decode_token(tenant_token)
#     tenant_id_str = tenant_data.get("tenant_id")
#     if not tenant_id_str:
#         return {"http_code": 401, "code": "UNAUTHORIZED", "message": "tenant_id missing in token"}
#     tenant_id = uuid.UUID(tenant_id_str)

#     payload = await request.json()
#     if payload.get("operation") != "create" or payload.get("target") != "asset":
#         return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")
    
#     entity = payload.get("entity", {})
#     device_name = entity.get("name")
#     device_type = entity.get("type")
#     parent_site_name = entity.get("parentName", None)
    
#     if not device_name or not device_type:
#         return HttpStatusCode.BAD_REQUEST.response(message="Device name and type required")

#     now = datetime.now().replace(tzinfo=None)

#     projects = await FRTUProjects.select(tenant_id=tenant_id)
#     if not projects:
#         return {"http_code": 404, "code": "NOT_FOUND", "message": "No projects found for this tenant"}
#     project_ids = [p.id for p in projects]

#     sites = await FRTUSites.select(project_id=project_ids)
#     if not sites:
#         return {"http_code": 404, "code": "NOT_FOUND", "message": "No sites found under tenant projects"}
    
#     site_obj = sites[0]
#     if parent_site_name:
#         filtered_sites = [s for s in sites if s.name == parent_site_name]
#         if filtered_sites:
#             site_obj = filtered_sites[0]
#     existing_devices = await FRTUDevices.select(site_id=site_obj.id, name=device_name)
#     if existing_devices:
#         device_obj = existing_devices[0]
#         device_id = device_obj.id
#     else:
#         device_obj = await FRTUDevices.insert(
#             site_id=site_obj.id,
#             name=device_name,
#             type=device_type,
#             attribute={"type": device_type},
#             creation_time=now,
#             last_update_time=now
#         )
#         device_id = device_obj.id

#     slots = await FRTUSlots.select(device_id=device_id)
#     if not slots or len(slots) < 11:
#         slot_names = [f"{device_name}_{str(i).zfill(2)}" for i in range(1, 12)]
#         slots = []
#         for sname in slot_names:
#             slot_obj = await FRTUSlots.insert(
#                 device_id=device_id,
#                 name=sname,
#                 creation_time=now,
#                 last_update_time=now
#             )
#             slots.append(slot_obj)
#     else:
#         slots.sort(key=lambda x: x.name)

#     devids_data = parse_devids_conf()
#     for idx, slot in enumerate(slots[:11], start=0):
#         if idx < 3:
#             module_type_name = ["PS", "COM", "SOM"][idx]
#             module_name = f"{slot.name}_FIXED"
#             type_flag = None
#         else:
#             conf = devids_data[idx - 3] if idx - 3 < len(devids_data) else None
#             if not conf or conf["type_flag"] == 0:
#                 continue
#             type_flag = conf["type_flag"]
#             module_type_name = "DI" if type_flag == 1 else "DO"
#             module_name = f"{slot.name}_{conf['module_id']}"

#         module_type_objs = await FRTUModuleType.select(name=module_type_name)
#         if module_type_objs:
#             module_type_obj = module_type_objs[0]
#         else:
#             module_type_obj = await FRTUModuleType.insert(
#                 name=module_type_name,
#                 description=f"{module_type_name} module",
#                 attribute={},
#                 creation_time=now,
#                 last_update_time=now
#             )

#         existing_module = await FRTUModules.select(slot_id=slot.id, name=module_name)
#         if existing_module:
#             continue

#         await FRTUModules.insert(
#             slot_id=slot.id,
#             name=module_name,
#             module_type=module_type_obj.id, 
#             description=f"{module_type_name} module",
#             creation_time=now,
#             last_update_time=now
#         )

#     return {"http_code": 201, "code": "CREATED", "message": f"Auto-discovery completed successfully for FRTU '{device_name}'."}

async def auto_discover_modules_msg(request: Request,authorization: str = Header(..., convert_underscores=False),a_name: str = Query(...),a_type: str = Query(...),settings: Settings = Depends(Settings.get_settings)):
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

        frtu_name = a_name.strip()
        frtu_type = a_type.strip().upper()
        now = datetime.now().replace(tzinfo=None)
        total_slots = 11
        fixed_slots = [1, 2, 3]

        devices = await FRTUDevices.select(name=frtu_name)
        if not devices:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Device '{frtu_name}' not found in DB"
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
                message=f"No slots found for device '{frtu_name}'"
            )
        slots.sort(key=lambda x: x.name)

        di_slots = []
        do_slots = []
        empty_slots = []
        modules_summary = {
            "Power Supply Identified in Slot": "1",
            "Communication Module Identified in Slot": "2",
            "SOM Module Identified in Slot": "3"
        }

        devids_data = parse_devids_conf()

        for idx, slot in enumerate(slots, start=1):
            if idx in fixed_slots:
                continue  

            module_records = await FRTUModules.select(slot_id=slot.id)
            module_type_name = None

            if module_records:
                module_type_id = module_records[0].module_type
                module_type_objs = await FRTUModuleType.select(id=module_type_id)
                module_type_name = module_type_objs[0].name if module_type_objs else None
            else:
                conf = next((c for c in devids_data if int(c.get("slot_no", -1)) == idx), None)
                if conf and int(conf.get("type_flag", 0)) in [1, 2]:
                    module_type_name = "DI" if conf["type_flag"] == 1 else "DO"

            if module_type_name == "DI":
                di_slots.append(str(idx))
            elif module_type_name == "DO":
                do_slots.append(str(idx))
            empty_slots = [
                str(i) for i in range(1, total_slots + 1)
                if str(i) not in di_slots + do_slots + [str(s) for s in fixed_slots]
            ]

        if di_slots:
            modules_summary["DI Module Identified in Slots"] = " / ".join(di_slots)
        if do_slots:
            modules_summary["DO Module Identified in Slots"] = " / ".join(do_slots)

        result = {
            "frtuName": frtu_name,
            "frtuType": frtu_type,
            "totalSlots": total_slots,
            "emptySlots": str(len(empty_slots)),
            "totalDI": str(len(di_slots)),
            "totalDO": str(len(do_slots)),
            "modules": modules_summary
        }

        return HttpStatusCode.OK.response(
            message=f"Auto-discovery summary for {frtu_name}",
            data=result
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

