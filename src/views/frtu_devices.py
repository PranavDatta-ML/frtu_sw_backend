from datetime import UTC, datetime, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Header, Request
from src.config.auth_config import ALGORITHM, SECRET_KEY
from src.enums.FrtuDeviceType import FrtuDeviceType
from src.models.frtu_modules import FRTUModules
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_sites import FRTUSites
from src.models.frtu_slots import FRTUSlots
from src.schemas.frtu_devices import FRTUDeviceCreate, FRTUDeviceUpdate
from src.models.frtu_devices import FRTUDevices
from src.utils.access_token import decode_token
from src.utils.schema import verify_schema
import jwt # type: ignore
from src import Settings, HttpStatusCode
import uuid


# async def create(request: Request, settings: Settings):
#     ok, messages, data = await verify_schema(await request.json(), FRTUDeviceCreate)

#     if not ok:
#         return HttpStatusCode.BAD_REQUEST.response(message=messages)

#     print(data.dict())

#     try:
#         value = await FRTUDevices.insert(**data.dict())
#         return HttpStatusCode.CREATED.response(message="FRTU Device created!", data=value)
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# async def create_device(data: dict, requester_id: UUID):

#     entity = data.get("entity") or {}

#     name = entity.get("name")
#     if not name:
#         return HttpStatusCode.BAD_REQUEST.response("Device name is required")

#     device_type = entity.get("type")
#     if not device_type:
#         return HttpStatusCode.BAD_REQUEST.response("Device type is required")

#     parent_name = entity.get("parentName")
#     raw_site_id = entity.get("site_id")

#     if raw_site_id:
#         try:
#             site_id = raw_site_id if isinstance(raw_site_id, UUID) else UUID(str(raw_site_id))
#         except:
#             return HttpStatusCode.BAD_REQUEST.response("Invalid site_id format")
#         site_rows = await FRTUSites.select(id=site_id)
#         if not site_rows:
#             return HttpStatusCode.NOT_FOUND.response("Site not found")
#         site_orm = site_rows[0]
#         site_row = {c.name: getattr(site_orm, c.name) for c in site_orm.__table__.columns}
#         site_attr = site_row.get("attribute") or {}
#         site_device_type = site_attr.get("device_type")
#         site_id = site_row["id"]
#         site_name = site_row["name"]
#     else:
#         if not parent_name:
#             return HttpStatusCode.BAD_REQUEST.response("Either site_id or parentName is required")
#         site_rows = await FRTUSites.select(name=parent_name)
#         if not site_rows:
#             return HttpStatusCode.NOT_FOUND.response("Site not found")
#         site_orm = site_rows[0]
#         site_row = {c.name: getattr(site_orm, c.name) for c in site_orm.__table__.columns}
#         site_attr = site_row.get("attribute") or {}
#         site_device_type = site_attr.get("device_type")
#         site_id = site_row["id"]
#         site_name = site_row["name"]

#     if site_device_type and site_device_type != device_type:
#         return HttpStatusCode.BAD_REQUEST.response(
#             f"Device type '{device_type}' does not match site device_type '{site_device_type}'"
#         )

#     existing = await FRTUDevices.select(name=name, site_id=site_id)
#     if existing:
#         return HttpStatusCode.BAD_REQUEST.response("Device already exists under this site")

#     attr = entity.copy()
#     attr.pop("site_id", None)
#     attr.pop("parentName", None)
#     attr["site_name"] = site_name

#     now = datetime.now(UTC).replace(tzinfo=None)

#     new_device = await FRTUDevices.insert(
#         name=name,
#         type=device_type,
#         site_id=site_id,
#         attribute=attr,
#         creation_time=now,
#         last_update_time=now
#     )

#     device_row = {c.name: getattr(new_device, c.name) for c in new_device.__table__.columns}

#     return HttpStatusCode.CREATED.response(
#         message="Device created successfully",
#         data={
#             "id": str(device_row["id"]),
#             "name": device_row["name"],
#             "type": device_row["type"],
#             "site_id": str(site_id),
#             "site_name": site_name,
#             "attribute": attr,
#             "creationTs": int(now.timestamp() * 1000),
#             "lastUpdateTs": int(now.timestamp() * 1000)
#         }
#     )

async def create_device(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}

    name = entity.get("name")
    if not name:
        return HttpStatusCode.BAD_REQUEST.response("Device name is required")

    device_type = entity.get("type")
    if not device_type:
        return HttpStatusCode.BAD_REQUEST.response("Device type is required")

    raw_site_id = entity.get("site_id")

    if not raw_site_id:
        return HttpStatusCode.BAD_REQUEST.response("site_id is required")

    try:
        site_id = raw_site_id if isinstance(raw_site_id, UUID) else UUID(str(raw_site_id))
    except:
        return HttpStatusCode.BAD_REQUEST.response("Invalid site_id format")

    site_rows = await FRTUSites.select(id=site_id)
    if not site_rows:
        return HttpStatusCode.NOT_FOUND.response("Site not found")

    site_orm = site_rows[0]
    site_row = {c.name: getattr(site_orm, c.name) for c in site_orm.__table__.columns}
    site_attr = site_row.get("attribute") or {}
    site_device_type = site_attr.get("device_type")
    site_name = site_row["name"]

    if site_device_type and site_device_type != device_type:
        return HttpStatusCode.BAD_REQUEST.response(
            f"Device type '{device_type}' does not match site device_type '{site_device_type}'"
        )

    existing = await FRTUDevices.select(name=name, site_id=site_id)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response("Device already exists under this site")

    attr = entity.copy()
    attr.pop("site_id", None)
    attr["site_name"] = site_name

    now = datetime.now(UTC).replace(tzinfo=None)

    new_device = await FRTUDevices.insert(
        name=name,
        type=device_type,
        site_id=site_id,
        attribute=attr,
        creation_time=now,
        last_update_time=now
    )

    device_row = {c.name: getattr(new_device, c.name) for c in new_device.__table__.columns}

    return HttpStatusCode.CREATED.response(
        message="Device created successfully",
        data={
            "id": str(device_row["id"]),
            "name": device_row["name"],
            "type": device_row["type"],
            "site_id": str(site_id),
            "site_name": site_name,
            "attribute": attr,
            "creationTs": int(now.timestamp() * 1000),
            "lastUpdateTs": int(now.timestamp() * 1000)
        }
    )



# ---------------- Read Devices ----------------
async def read_devices(data: dict, requester_id: UUID, name: str | None, page: int, limit: int):

    entity = data.get("entity") or {}
    payload_name = entity.get("name") if isinstance(entity, dict) else None
    final_search = payload_name or name or None

    all_rows = await FRTUDevices.select()
    device_list = []

    for row in all_rows:
        device_row = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        attr = device_row.get("attribute") or {}

        device_list.append({
            "id": str(device_row["id"]),
            "site_id": str(device_row["site_id"]),
            "name": device_row["name"],
            "type": device_row["type"],
            "label": attr.get("label"),
            "description": attr.get("description"),
            "module": attr.get("module"),
            "no_of_Slave_Rack": attr.get("no_of_Slave_Rack"),
            "creationTs": int(device_row["creation_time"].timestamp() * 1000) if device_row.get("creation_time") else None,
            "lastUpdateTs": int(device_row["last_update_time"].timestamp() * 1000) if device_row.get("last_update_time") else None,
            "site_name": attr.get("site_name"),
            "attribute": attr
        })

    if final_search:
        final_search = final_search.lower()
        device_list = [d for d in device_list if final_search in d["name"].lower()]

    total_records = len(device_list)
    total_pages = (total_records + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit
    paginated_devices = device_list[start:end]

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Devices fetched successfully",
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": total_pages,
        "devices": paginated_devices
    }


async def read_device_by_id(device_id: UUID, requester_id: UUID, data: dict):

    try:
        device_id = device_id if isinstance(device_id, UUID) else UUID(str(device_id))
    except:
        return HttpStatusCode.BAD_REQUEST.response("Invalid device ID format")

    rows = await FRTUDevices.select(id=device_id)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Device not found")

    orm = rows[0]
    device_row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}

    attr = device_row.get("attribute") or {}
    site_id = device_row["site_id"]

    site_rows = await FRTUSites.select(id=site_id)
    site_name = ""
    if site_rows:
        s = site_rows[0]
        sdict = {c.name: getattr(s, c.name) for c in s.__table__.columns}
        site_name = sdict["name"]

    device_obj = {
        "id": str(device_row["id"]),
        "site_id": str(site_id),
        "site_name": site_name,
        "name": device_row["name"],
        "type": device_row["type"],
        "creationTs": int(device_row["creation_time"].timestamp() * 1000) if device_row.get("creation_time") else None,
        "lastUpdateTs": int(device_row["last_update_time"].timestamp() * 1000) if device_row.get("last_update_time") else None
    }

    for k, v in attr.items():
        device_obj[k] = v

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Device fetched successfully",
        "count": 1,
        "devices": [device_obj]
    }

# ------------------Read Devices By Name or ID------------------
async def read_device(data: dict, requester_id: UUID, page: int, limit: int):

    entity = data.get("entity") or {}
    search_name = entity.get("name")
    raw_device_id = entity.get("device_id")

    if raw_device_id:
        try:
            device_id = raw_device_id if isinstance(raw_device_id, UUID) else UUID(str(raw_device_id))
        except:
            return HttpStatusCode.BAD_REQUEST.response("Invalid device ID format")

        rows = await FRTUDevices.select(id=device_id)
        if not rows:
            return HttpStatusCode.NOT_FOUND.response("Device not found")

        orm = rows[0]
        device_row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}
        attr = device_row.get("attribute") or {}

        site_id = device_row["site_id"]
        site_rows = await FRTUSites.select(id=site_id)
        site_name = ""
        if site_rows:
            s = site_rows[0]
            sdict = {c.name: getattr(s, c.name) for c in s.__table__.columns}
            site_name = sdict["name"]

        device_obj = {
            "id": str(device_row["id"]),
            "site_id": str(site_id),
            "site_name": site_name,
            "name": device_row["name"],
            "type": device_row["type"],
            "creationTs": int(device_row["creation_time"].timestamp() * 1000) if device_row.get("creation_time") else None,
            "lastUpdateTs": int(device_row["last_update_time"].timestamp() * 1000) if device_row.get("last_update_time") else None
        }

        for k, v in attr.items():
            device_obj[k] = v

        return {
            "http_code": 200,
            "code": "OK",
            "message": "Device fetched successfully",
            "count": 1,
            "devices": [device_obj]
        }

    all_rows = await FRTUDevices.select()
    device_list = []

    for row in all_rows:
        device_row = {c.name: getattr(row, c.name) for c in row.__table__.columns}
        attr = device_row.get("attribute") or {}

        device_list.append({
            "id": str(device_row["id"]),
            "site_id": str(device_row["site_id"]),
            "name": device_row["name"],
            "type": device_row["type"],
            "label": attr.get("label"),
            "description": attr.get("description"),
            "module": attr.get("module"),
            "no_of_Slave_Rack": attr.get("no_of_Slave_Rack"),
            "creationTs": int(device_row["creation_time"].timestamp() * 1000) if device_row.get("creation_time") else None,
            "lastUpdateTs": int(device_row["last_update_time"].timestamp() * 1000) if device_row.get("last_update_time") else None,
            "site_name": attr.get("site_name")
        })

    if search_name:
        search = search_name.lower()
        device_list = [d for d in device_list if search in d["name"].lower()]

    total_records = len(device_list)
    total_pages = (total_records + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit
    paginated = device_list[start:end]

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Devices fetched successfully",
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": total_pages,
        "devices": paginated
    }


# ---------------- Update Device ----------------
async def update_device_by_name(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}
    device_name = entity.get("name")

    if not device_name:
        return HttpStatusCode.BAD_REQUEST.response("Device name is required")

    rows = await FRTUDevices.select(name=device_name)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Device not found")

    orm = rows[0]
    device_row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}

    site_id = (
        device_row.get("site_id")
        or device_row.get("siteid")
        or device_row.get("siteId")
        or device_row.get("siteID")
    )

    device_id = device_row["id"]
    existing_attr = device_row.get("attribute") or {}

    updated_attr = existing_attr.copy()

    new_name = device_row["name"]

    for key, value in entity.items():
        if key == "name":
            continue
        if value is not None:
            updated_attr[key] = value

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUDevices.update(
        conditions={"id": device_id},
        attribute=updated_attr,
        last_update_time=now
    )

    site_name = ""
    if site_id:
        site_rows = await FRTUSites.select(id=site_id)
        if site_rows:
            s = site_rows[0]
            sdict = {c.name: getattr(s, c.name) for c in s.__table__.columns}
            site_name = sdict.get("name")

    device_obj = {
        "id": str(device_id),
        "site_id": str(site_id) if site_id else None,
        "site_name": site_name,
        "name": new_name,
        "type": device_row["type"],
        "creationTs": int(device_row["creation_time"].timestamp() * 1000)
        if device_row.get("creation_time") else None,
        "lastUpdateTs": int(now.timestamp() * 1000)
    }

    for k, v in updated_attr.items():
        device_obj[k] = v

    return HttpStatusCode.OK.response(
        message="Device updated successfully",
        data=device_obj
    )

async def update_device_by_id(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}
    raw_id = entity.get("id") or entity.get("device_id")

    if not raw_id:
        return HttpStatusCode.BAD_REQUEST.response("Device ID is required")

    try:
        device_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
    except:
        return HttpStatusCode.BAD_REQUEST.response("Invalid device ID format")

    rows = await FRTUDevices.select(id=device_id)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Device not found")

    orm = rows[0]
    device_row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}

    site_id = (
        device_row.get("site_id")
        or device_row.get("siteid")
        or device_row.get("siteId")
        or device_row.get("siteID")
    )

    existing_attr = device_row.get("attribute") or {}
    updated_attr = existing_attr.copy()

    new_name = device_row["name"]

    for key, value in entity.items():
        if key in ["id", "device_id"]:
            continue
        if key == "name" and value:
            new_name = value
        elif value is not None:
            updated_attr[key] = value

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUDevices.update(
        conditions={"id": device_id},
        name=new_name,
        attribute=updated_attr,
        last_update_time=now
    )

    site_name = ""
    if site_id:
        site_rows = await FRTUSites.select(id=site_id)
        if site_rows:
            s = site_rows[0]
            sd = {c.name: getattr(s, c.name) for c in s.__table__.columns}
            site_name = sd.get("name")

    device_obj = {
        "id": str(device_id),
        "site_id": str(site_id) if site_id else None,
        "site_name": site_name,
        "name": new_name,
        "type": device_row["type"],
        "creationTs": int(device_row["creation_time"].timestamp() * 1000)
        if device_row.get("creation_time") else None,
        "lastUpdateTs": int(now.timestamp() * 1000)
    }

    for k, v in updated_attr.items():
        device_obj[k] = v

    return HttpStatusCode.OK.response(
        message="Device updated successfully",
        data=device_obj
    )

async def delete_device(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}
    raw_id = entity.get("id") or entity.get("device_id")

    if not raw_id:
        return HttpStatusCode.BAD_REQUEST.response("Device ID is required")

    try:
        device_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
    except:
        return HttpStatusCode.BAD_REQUEST.response("Invalid device ID format")

    rows = await FRTUDevices.select(id=device_id)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Device not found")

    device = rows[0]

    slots = await FRTUSlots.select(device_id=device_id)
    slot_count = len(slots)
    if slot_count == 0:
        await FRTUDevices.delete(conditions={"id": device_id})
        return HttpStatusCode.OK.response(
            message="Device deleted successfully (no slots found)",
            data={"device_id": str(device_id)}
        )
    for s in slots:
        attr = getattr(s, "attribute") or {}
        module = attr.get("module") or attr.get("module_type") or None

        if module:
            return HttpStatusCode.BAD_REQUEST.response(
                f"Cannot delete device. Slot '{s.name}' contains module '{module}'."
            )
    await FRTUSlots.delete(conditions={"device_id": device_id})
    await FRTUDevices.delete(conditions={"id": device_id})

    return HttpStatusCode.OK.response(
        message="Device and all empty slots deleted successfully",
        data={"device_id": str(device_id)}
    )



# ---------------- Delete Device ----------------
# async def delete_device(
#     request: Request,
#     authorization: str = Header(..., convert_underscores=False),
#     settings: Settings = Depends(Settings.get_settings)
# ):
#     if not authorization or not authorization.startswith("Bearer "):
#         return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid Authorization header"}

#     tenant_token = authorization.split(" ")[1]
#     try:
#         tenant_data = decode_token(tenant_token)
#     except Exception as e:
#         return {"http_code": 401, "code": "UNAUTHORIZED", "message": f"Tenant token decode failed: {str(e)}"}

#     tenant_id_str = tenant_data.get("tenant_id")
#     if not tenant_id_str:
#         return {"http_code": 401, "code": "UNAUTHORIZED", "message": "Invalid tenant token: tenant_id missing"}

#     try:
#         tenant_id = uuid.UUID(tenant_id_str)
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

#     payload = await request.json()
#     if payload.get("operation") != "delete" or payload.get("target") != "device":
#         return HttpStatusCode.BAD_REQUEST.response(
#             message="Invalid request: operation must be 'delete' and target must be 'device'"
#         )

#     entity = payload.get("entity") or {}
#     device_name = entity.get("name")
#     if not device_name:
#         return HttpStatusCode.BAD_REQUEST.response(message="Device 'name' is required to delete")

#     try:
#         device = await FRTUDevices.select(name=device_name)
#         if not device:
#             return {"http_code": 404, "code": "NOT_FOUND", "message": f"Device '{device_name}' not found"}

#         device_obj = device[0]

#         # Verify tenant access via site -> project
#         site = await FRTUSites.select(id=device_obj.site_id)
#         if not site:
#             return {"http_code": 404, "code": "NOT_FOUND", "message": f"Site for device '{device_name}' not found"}
#         site_obj = site[0]

#         parent_project = await FRTUProjects.select(id=site_obj.project_id, tenant_id=tenant_id)
#         if not parent_project:
#             return {"http_code": 403, "code": "FORBIDDEN",
#                     "message": f"Tenant does not have access to the project of device '{device_name}'"}

#         # Delete all slots of this device first
#         slots = await FRTUSlots.select(device_id=device_obj.id)
#         for slot in slots:
#             await FRTUSlots.delete(conditions={"id": slot.id})

#         # Delete the device
#         await FRTUDevices.delete(conditions={"id": device_obj.id})

#         return {"http_code": 200, "code": "OK", "message": f"Device '{device_name}' and its slots deleted successfully"}

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=f"Failed to delete device: {str(e)}")

# ---------------- Delete Device ----------------
