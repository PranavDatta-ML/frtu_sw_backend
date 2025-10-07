from datetime import datetime
import uuid, os
from uuid import UUID
from fastapi import HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_modules import FRTUModules
from src.models.frtu_module_type import FRTUModuleType
from src import HttpStatusCode
import jwt
from src.config.auth_config import ALGORITHM, SECRET_KEY

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVIDS_CONF_PATH = os.path.join(BASE_DIR, "config", "devids.conf")

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def get_slot_name_by_id(slot_id: str):
    slot = await FRTUSlots.get_or_none(id=slot_id)
    return slot.name if slot else None

async def get_module_type_name_by_id(module_type_id: str):
    module_type = await FRTUModuleType.get_or_none(id=module_type_id)
    return module_type.name if module_type else None


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

# ---------------- Auto Discover Modules ----------------
async def auto_discover_modules(request: Request, authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}
    
    tenant_token = authorization.split(" ")[1]
    tenant_data = decode_token(tenant_token)
    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return {"http_code": 401, "code": "UNAUTHORIZED", "message": "tenant_id missing in token"}
    tenant_id = uuid.UUID(tenant_id_str)

    payload = await request.json()
    if payload.get("operation") != "create" or payload.get("target") != "asset":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")
    
    entity = payload.get("entity", {})
    device_name = entity.get("name")
    device_type = entity.get("type")
    parent_site_name = entity.get("parentName", None)
    
    if not device_name or not device_type:
        return HttpStatusCode.BAD_REQUEST.response(message="Device name and type required")

    now = datetime.now().replace(tzinfo=None)

    projects = await FRTUProjects.select(tenant_id=tenant_id)
    if not projects:
        return {"http_code": 404, "code": "NOT_FOUND", "message": "No projects found for this tenant"}
    project_ids = [p.id for p in projects]

    sites = await FRTUSites.select(project_id=project_ids)
    if not sites:
        return {"http_code": 404, "code": "NOT_FOUND", "message": "No sites found under tenant projects"}
    
    site_obj = sites[0]
    if parent_site_name:
        filtered_sites = [s for s in sites if s.name == parent_site_name]
        if filtered_sites:
            site_obj = filtered_sites[0]
    existing_devices = await FRTUDevices.select(site_id=site_obj.id, name=device_name)
    if existing_devices:
        device_obj = existing_devices[0]
        device_id = device_obj.id
    else:
        device_obj = await FRTUDevices.insert(
            site_id=site_obj.id,
            name=device_name,
            type=device_type,
            attribute={"type": device_type},
            creation_time=now,
            last_update_time=now
        )
        device_id = device_obj.id

    slots = await FRTUSlots.select(device_id=device_id)
    if not slots or len(slots) < 11:
        slot_names = [f"{device_name}_{str(i).zfill(2)}" for i in range(1, 12)]
        slots = []
        for sname in slot_names:
            slot_obj = await FRTUSlots.insert(
                device_id=device_id,
                name=sname,
                creation_time=now,
                last_update_time=now
            )
            slots.append(slot_obj)
    else:
        slots.sort(key=lambda x: x.name)

    devids_data = parse_devids_conf()
    for idx, slot in enumerate(slots[:11], start=0):
        if idx < 3:
            module_type_name = ["PS", "COM", "SOM"][idx]
            module_name = f"{slot.name}_FIXED"
            type_flag = None
        else:
            conf = devids_data[idx - 3] if idx - 3 < len(devids_data) else None
            if not conf or conf["type_flag"] == 0:
                continue
            type_flag = conf["type_flag"]
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

        existing_module = await FRTUModules.select(slot_id=slot.id, name=module_name)
        if existing_module:
            continue

        await FRTUModules.insert(
            slot_id=slot.name,
            name=module_name,
            module_type=module_type_name, 
            description=f"{module_type_name} module",
            creation_time=now,
            last_update_time=now
        )

    return {"http_code": 201, "code": "CREATED", "message": f"Auto-discovery completed successfully for FRTU '{device_name}'."}


# ---------------- Auto Discover Modules Message ----------------
# async def auto_discover_modules_msg(request: Request, a_name: str, a_type: str, authorization: str = Header(...)):
#     try:
#         if not authorization or not authorization.startswith("Bearer "):
#             return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}
        
#         token = authorization.split(" ")[1]
#         tenant_data = decode_token(token) 
#         tenant_id_str = tenant_data.get("tenant_id")
#         if not tenant_id_str:
#             return JSONResponse(status_code=401, content={"status":"error","message":"tenant_id missing in token"})
#         tenant_id = UUID(tenant_id_str)

#         devices = await FRTUDevices.select(name=a_name, type=a_type.upper())
#         if not devices:
#             return JSONResponse(status_code=404, content={"status":"error","message":"Device not found"})
#         device = devices[0]

#         slots = await FRTUSlots.select(device_id=device.id)
#         slots.sort(key=lambda s: s.name)  
#         total_slots = len(slots)

#         modules = await FRTUModules.select(slot_id=[s.id for s in slots])
#         module_type_map = {}
#         for m in modules:
#             m_type = await FRTUModuleType.select(id=m.module_type)
#             module_type_name = m_type[0].name if m_type else "Unknown"
#             key = f"{module_type_name} Module Identified in Slots"
#             if key not in module_type_map:
#                 module_type_map[key] = []
#             slot_no = "".join(filter(str.isdigit, [s.name for s in slots if s.id == m.slot_id][0]))
#             module_type_map[key].append(slot_no)

#         total_DI = sum([len(v) for k, v in module_type_map.items() if k.startswith("DI")])
#         total_DO = sum([len(v) for k, v in module_type_map.items() if k.startswith("DO")])
#         filled_slots = sum([len(v) for v in module_type_map.values()])
#         empty_slots = total_slots - filled_slots

#         modules_resp = {k: " / ".join(v) if v else "None" for k, v in module_type_map.items()}

#         response = {
#             "frtuName": device.name,
#             "frtuType": device.type,
#             "totalSlots": total_slots,
#             "emptySlots": str(empty_slots),
#             "totalDI": str(total_DI),
#             "totalDO": str(total_DO),
#             "modules": modules_resp
#         }

#         return JSONResponse(status_code=200, content=response)

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})  
    
async def auto_discover_modules_msg(request: Request, a_name: str = Query(...), a_type: str = Query(...)):
    try:
        frtu_name = a_name.strip()
        frtu_type = a_type.strip().upper()
        now = datetime.now().replace(tzinfo=None)

        devices = await FRTUDevices.select(name=frtu_name)
        if not devices:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Device '{frtu_name}' not found in DB"
            )
        device_obj = devices[0]

        slots = await FRTUSlots.select(device_id=device_obj.id)
        if not slots:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No slots found for device '{frtu_name}'"
            )
        slots.sort(key=lambda x: x.name)

        total_slots = 11
        total_di = 0
        total_do = 0
        empty_slots = []
        di_slots = []
        do_slots = []
        modules_summary = {}

        modules_summary["Power Supply Identified in Slot"] = "1"
        modules_summary["Communication Module Identified in Slot"] = "2"
        modules_summary["SOM Module Identified in Slot"] = "3"

        devids_data = parse_devids_conf()

        for idx, slot in enumerate(slots, start=1):
            if idx <= 3:
                continue  
            module_records = await FRTUModules.select(slot_id=slot.id)
            if module_records:
                module_type_id = module_records[0]["module_type"]
                module_type_obj = await FRTUModuleType.get_or_none(id=module_type_id)
                module_type_name = module_type_obj.name if module_type_obj else "UNKNOWN"
            else:
                conf = next((c for c in devids_data if c["slot_no"] == idx), None)
                if not conf or conf["type_flag"] == 0:
                    empty_slots.append(str(idx))
                    continue
                module_type_name = "DI" if conf["type_flag"] == 1 else "DO"

            if module_type_name == "DI":
                total_di += 1
                di_slots.append(str(idx))
            elif module_type_name == "DO":
                total_do += 1
                do_slots.append(str(idx))
            else:
                empty_slots.append(str(idx))

        if di_slots:
            modules_summary["DI Module Identified in Slots"] = " / ".join(di_slots)
        if do_slots:
            modules_summary["DO Module Identified in Slots"] = " / ".join(do_slots)

        result = {
            "frtuName": frtu_name,
            "frtuType": frtu_type,
            "totalSlots": total_slots,
            "emptySlots": str(len(empty_slots)),
            "totalDI": str(total_di),
            "totalDO": str(total_do),
            "modules": modules_summary
        }

        return HttpStatusCode.OK.response(
            message=f"Auto-discovery summary for {frtu_name}",
            data=result
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

