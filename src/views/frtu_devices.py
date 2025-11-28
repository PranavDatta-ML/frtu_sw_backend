from datetime import UTC, datetime, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy import select
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



# ---------------- Create Device ----------------
async def create_device(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}

    name = entity.get("name")
    if not name:
        return HttpStatusCode.BAD_REQUEST.response("Device name is required")

    device_type = entity.get("type")
    if not device_type:
        return HttpStatusCode.BAD_REQUEST.response("Device type is required")

    parent_name = entity.get("parentName")
    raw_site_id = entity.get("site_id")

    if raw_site_id:
        try:
            site_id = raw_site_id if isinstance(raw_site_id, UUID) else UUID(str(raw_site_id))
        except:
            return HttpStatusCode.BAD_REQUEST.response("Invalid site_id format")
        site_rows = await FRTUSites.select(id=site_id)
        if not site_rows:
            return HttpStatusCode.NOT_FOUND.response("Site not found")
        site_orm = site_rows[0]
        site_row = {c.name: getattr(site_orm, c.name) for c in site_orm.__table__.columns}
        site_id = site_row["id"]
        site_name = site_row["name"]
    else:
        if not parent_name:
            return HttpStatusCode.BAD_REQUEST.response("Either site_id or parentName is required")
        site_rows = await FRTUSites.select(name=parent_name)
        if not site_rows:
            return HttpStatusCode.NOT_FOUND.response("Site not found")
        site_orm = site_rows[0]
        site_row = {c.name: getattr(site_orm, c.name) for c in site_orm.__table__.columns}
        site_id = site_row["id"]
        site_name = site_row["name"]

    existing = await FRTUDevices.select(name=name, site_id=site_id)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response("Device already exists under this site")

    attr = entity.copy()
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
async def read_devices(request: Request,authorization: str = Header(..., convert_underscores=False),settings: Settings = Depends(Settings.get_settings)):
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

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

    payload = await request.json()
    entity = payload.get("entity", {})
    device_name = entity.get("name")

    if payload.get("operation") != "read" or payload.get("target") != "device":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

    try:
        tenant_projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not tenant_projects:
            return {"http_code": 404, "code": "NOT_FOUND", "message": "No projects found for this tenant"}

        project_ids = [p.id for p in tenant_projects]

        site_filters = {"project_id": project_ids}
        if device_name:
            pass
        sites = await FRTUSites.select(**site_filters)
        if not sites:
            return {"http_code": 404, "code": "NOT_FOUND", "message": "No sites found for these projects"}

        response_devices = []
        for site in sites:
            site_dict = dict(site)
            site_id = site_dict.get("id")
            site_name = site_dict.get("name")

            device_filters = {"site_id": site_id}
            if device_name:
                device_filters["name"] = device_name
            devices = await FRTUDevices.select(**device_filters)

            for device in devices:
                dev_dict = dict(device)
                attrs = dev_dict.pop("attribute", {}) or {}
                for k, v in attrs.items():
                    dev_dict[k] = v

                dev_dict["id"] = str(dev_dict["id"])
                dev_dict["parentName"] = site_name
                dev_dict["creationTs"] = int(dev_dict["creation_time"].timestamp() * 1000) if dev_dict.get("creation_time") else None
                dev_dict["lastUpdateTs"] = int(dev_dict["last_update_time"].timestamp() * 1000) if dev_dict.get("last_update_time") else None

                response_devices.append(dev_dict)

        if device_name and response_devices:
            response_devices = [d for d in response_devices if d["name"] == device_name]

        return {"count": len(response_devices), "devices": response_devices}

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# ---------------- Update Device ----------------
async def update_device(request: Request,authorization: str = Header(..., convert_underscores=False),settings: Settings = Depends(Settings.get_settings)):
    if not authorization or not authorization.startswith("Bearer "):
        return {
            "http_code": 401,
            "code": "UNAUTHORIZED",
            "message": "Invalid Authorization header"
        }

    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return {
            "http_code": 401,
            "code": "UNAUTHORIZED",
            "message": f"Tenant token decode failed: {str(e)}"
        }

    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return {
            "http_code": 401,
            "code": "UNAUTHORIZED",
            "message": "Invalid tenant token: tenant_id missing"
        }

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

    payload = await request.json()
    if payload.get("operation") != "update" or payload.get("target") != "device":
        return HttpStatusCode.BAD_REQUEST.response(
            message="Invalid request: operation must be 'update' and target must be 'device'"
        )

    entity = payload.get("entity") or {}
    device_name = entity.get("name")
    if not device_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Device 'name' is required to update")

    try:
        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if not projects:
            return {
                "http_code": 404,
                "code": "NOT_FOUND",
                "message": "No projects found for this tenant"
            }
        project_ids = [p.id for p in projects]

        sites = await FRTUSites.select(project_id=project_ids)
        if not sites:
            return {
                "http_code": 404,
                "code": "NOT_FOUND",
                "message": "No sites found for tenant projects"
            }
        site_ids = [s.id for s in sites]

        devices = await FRTUDevices.select(site_id=site_ids, name=device_name)
        if not devices:
            return {
                "http_code": 404,
                "code": "NOT_FOUND",
                "message": f"No device named '{device_name}' found"
            }

        device_obj = devices[0]

        site_obj = await FRTUSites.select(id=device_obj["site_id"])
        if not site_obj:
            return {
                "http_code": 403,
                "code": "FORBIDDEN",
                "message": f"Tenant does not have access to the site of device '{device_name}'"
            }
        site_obj = site_obj[0]

        parent_project = await FRTUProjects.select(id=site_obj["project_id"], tenant_id=tenant_id)
        if not parent_project:
            return {
                "http_code": 403,
                "code": "FORBIDDEN",
                "message": f"Tenant does not have access to the project of device '{device_name}'"
            }

        exclude_keys = {"name", "type", "site_id"}
        existing_attrs = dict(device_obj.get("attribute") or {})
        for k, v in entity.items():
            if k not in exclude_keys:
                existing_attrs[k] = v
        existing_attrs["type"] = device_obj["type"] 

        now = datetime.now(UTC).replace(tzinfo=None)

        await FRTUDevices.update(
            conditions={"id": device_obj["id"]},
            attribute=existing_attrs,
            last_update_time=now
        )

        return {
            "http_code": 200,
            "code": "OK",
            "message": f"Device '{device_name}' updated successfully"
        }

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Failed to update device: {str(e)}")


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
async def delete_device(
    request: Request,
    authorization: str = Header(..., convert_underscores=False),
    settings: Settings = Depends(Settings.get_settings)
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

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

    payload = await request.json()
    if payload.get("operation") != "delete" or payload.get("target") != "device":
        return HttpStatusCode.BAD_REQUEST.response(
            message="Invalid request: operation must be 'delete' and target must be 'device'"
        )

    entity = payload.get("entity") or {}
    device_name = entity.get("name")
    if not device_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Device 'name' is required to delete")

    try:
        device = await FRTUDevices.select(name=device_name)
        if not device:
            return {"http_code": 404, "code": "NOT_FOUND", "message": f"Device '{device_name}' not found"}

        device_obj = device[0]

        site = await FRTUSites.select(id=device_obj.site_id)
        if not site:
            return {"http_code": 404, "code": "NOT_FOUND", "message": f"Site for device '{device_name}' not found"}
        site_obj = site[0]

        parent_project = await FRTUProjects.select(id=site_obj.project_id, tenant_id=tenant_id)
        if not parent_project:
            return {"http_code": 403, "code": "FORBIDDEN",
                    "message": f"Tenant does not have access to the project of device '{device_name}'"}

        slots = await FRTUSlots.select(device_id=device_obj.id)
        for slot in slots:
            modules = await FRTUModules.select(slot_id=slot.id)
            for module in modules:
                await FRTUModules.delete(conditions={"id": module.id})
        
        for slot in slots:
            await FRTUSlots.delete(conditions={"id": slot.id})

        await FRTUDevices.delete(conditions={"id": device_obj.id})

        return {"http_code": 200, "code": "OK", "message": f"Device '{device_name}' and its slots/modules deleted successfully"}

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Failed to delete device: {str(e)}")
    
