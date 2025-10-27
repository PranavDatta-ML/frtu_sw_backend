from datetime import UTC, datetime
import uuid
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, Header, Request
from src.config.auth_config import ALGORITHM, SECRET_KEY
from src.models.frtu_devices import FRTUDevices
from src.schemas.frtu_projects import FRTUProjectCreate
from src.models.frtu_sites import FRTUSites
from src.models.frtu_projects import FRTUProjects
from src import Settings, HttpStatusCode
from src.utils.access_token import decode_token
from src.utils.schema import verify_schema
import jwt # type: ignore


# ---------------- Create Site ----------------
async def create_site(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):

    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401,"code": "UNAUTHORIZED","message": "Invalid Authorization header"}

    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return {"http_code": 401,"code": "UNAUTHORIZED","message": f"Tenant token decode failed: {str(e)}"}

    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return {"http_code": 401,"code": "UNAUTHORIZED","message": "Invalid tenant token: tenant_id missing"}

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Invalid tenant_id in token: {str(e)}")

    payload = await request.json()
    if payload.get("operation") != "create" or payload.get("target") != "site":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid request: operation must be 'create' and target must be 'site'")

    entity = payload.get("entity") or {}
    name = entity.get("name")
    site_type = entity.get("type")
    parent_name = entity.get("parentName")

    if not name or not site_type or not parent_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Site 'name', 'type' and 'parentName' are required fields")

    parent_project = await FRTUProjects.select(tenant_id=tenant_id, name=parent_name)
    if not parent_project:
        return HttpStatusCode.NOT_FOUND.response(message=f"Tenant has no project named '{parent_name}'")

    existing = await FRTUSites.select(project_id=parent_project[0].id, name=name)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response(message=f"Site with name '{name}' already exists in project '{parent_name}'")

    exclude_keys = {"name", "type", "parentName"}
    attributes = {k: v for k, v in entity.items() if k not in exclude_keys}
    attributes["type"] = site_type

    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        await FRTUSites.insert(
            project_id=parent_project[0].id,
            name=name,
            attribute=attributes,
            creation_time=now,
            last_update_time=now
        )

        return {"http_code": 201, "code": "CREATED", "message": "FRTU Site created!"}

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# ---------------- Read Sites ---------------- 
async def read_sites(
    request: Request,
    authorization: str = Header(..., convert_underscores=False),
    settings: Settings = Depends(Settings.get_settings)
):
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
    entity = payload.get("entity", {})
    site_name = entity.get("name")
    project_name = entity.get("projectName")  

    if payload.get("operation") != "read" or payload.get("target") != "site":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

    try:
        filters = {}

        if project_name:
            parent_projects = await FRTUProjects.select(tenant_id=tenant_id, name=project_name)
            if not parent_projects:
                return {
                    "http_code": 404,
                    "code": "NOT_FOUND",
                    "message": f"Tenant has no project named '{project_name}'"
                }
            filters["project_id"] = parent_projects[0].id

        if site_name:
            filters["name"] = site_name

        if not filters:
            parent_projects = await FRTUProjects.select(tenant_id=tenant_id)
            if not parent_projects:
                return {
                    "http_code": 404,
                    "code": "NOT_FOUND",
                    "message": "No projects found for this tenant"
                }
            filters["project_id"] = [p.id for p in parent_projects]

        sites = await FRTUSites.select(**filters)
        if not sites:
            return {
                "http_code": 404,
                "code": "NOT_FOUND",
                "message": f"Tenant does not have site {site_name}!" if site_name else "No sites found for this tenant"
            }

        response_sites = []
        for site in sites:
            site_dict = dict(site)
            attrs = site_dict.pop("attribute", {}) or {}
            for k, v in attrs.items():
                site_dict[k] = v

            parent_project = await FRTUProjects.select(id=site_dict.get("project_id"))
            site_dict["parentName"] = parent_project[0].name if parent_project else None

            from src.models.frtu_devices import FRTUDevices
            devices = await FRTUDevices.select(site_id=site_dict.get("id"))
            if devices:
                site_dict["childNames"] = [d.name for d in devices]

            site_dict["id"] = str(site_dict["id"])
            site_dict["creationTs"] = int(site_dict["creation_time"].timestamp() * 1000) if site_dict.get("creation_time") else None
            site_dict["lastUpdateTs"] = int(site_dict["last_update_time"].timestamp() * 1000) if site_dict.get("last_update_time") else None

            site_dict["type"] = "site"
            site_dict["status"] = site_dict.get("status", "0")
            site_dict["deviceType"] = site_dict.get("type", "FRTU")
            site_dict.pop("creation_time", None)
            site_dict.pop("last_update_time", None)
            site_dict.pop("project_id", None)

            response_sites.append(site_dict)

        return {
            "count": len(response_sites),
            "sites": response_sites
        }

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# ---------------- Update Site ----------------
async def update_site(request: Request, authorization: str = Header(..., convert_underscores=False), settings: Settings = Depends(Settings.get_settings)):

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
    if payload.get("operation") != "update" or payload.get("target") != "site":
        return HttpStatusCode.BAD_REQUEST.response(
            message="Invalid request: operation must be 'update' and target must be 'site'"
        )

    entity = payload.get("entity") or {}
    site_name = entity.get("name")
    if not site_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Site 'name' is required to update")

    try:
        site = await FRTUSites.select(name=site_name)
        if not site:
            return {
                "http_code": 404,
                "code": "NOT_FOUND",
                "message": f"Site '{site_name}' not found"
            }

        site_obj = site[0]

        parent_project = await FRTUProjects.select(id=site_obj.project_id, tenant_id=tenant_id)
        if not parent_project:
            return {
                "http_code": 403,
                "code": "FORBIDDEN",
                "message": f"Tenant does not have access to the project of site '{site_name}'"
            }

        exclude_keys = {"name", "type", "project_id"}
        updated_attrs = {k: v for k, v in entity.items() if k not in exclude_keys}

        existing_attrs = site_obj.attribute or {}
        existing_attrs.update(updated_attrs)

        now = datetime.now(UTC).replace(tzinfo=None)

        await FRTUSites.update(
            conditions={"name": site_name},
            attribute=existing_attrs,
            last_update_time=now
        )

        response_data = dict(site_obj)
        response_data.pop("attribute", None)
        response_data.update(existing_attrs)
        response_data["parentName"] = parent_project[0].name
        response_data.pop("project_id", None)

        if response_data.get("creation_time"):
            response_data["creation_time"] = response_data["creation_time"].isoformat()
        if response_data.get("last_update_time"):
            response_data["last_update_time"] = response_data["last_update_time"].isoformat()
        if response_data.get("id"):
            response_data["id"] = str(response_data["id"])

        return {
            "http_code": 200,
            "code": "OK",
            "message": f"Site '{site_name}' updated successfully"
        }

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# ---------------- Delete Site ----------------
async def delete_site(request: Request,authorization: str = Header(..., convert_underscores=False),settings: Settings = Depends(Settings.get_settings)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"http_code": 401,"code": "UNAUTHORIZED","message": "Invalid Authorization header"}

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
    if payload.get("operation") != "delete" or payload.get("target") != "site":
        return HttpStatusCode.BAD_REQUEST.response(
            message="Invalid request: operation must be 'delete' and target must be 'site'"
        )

    entity = payload.get("entity") or {}
    site_name = entity.get("name")
    if not site_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Site 'name' is required to delete")

    try:
        site = await FRTUSites.select(name=site_name)
        if not site:
            return {"http_code": 404,"code": "NOT_FOUND","message": f"Tenant does not have Site {site_name}!"}

        site_obj = site[0]

        parent_project = await FRTUProjects.select(id=site_obj.project_id, tenant_id=tenant_id)
        if not parent_project:
            return {"http_code": 403,"code": "FORBIDDEN","message": f"Tenant does not have access to the project of site '{site_name}'"}

        devices = await FRTUDevices.select(site_id=site_obj.id)
        if devices:
            return {"http_code": 400,"code": "BAD_REQUEST","message": f"Site '{site_name}' has {len(devices)} device(s). Delete them first."}

        await FRTUSites.delete(conditions={"id": site_obj.id})

        return {"http_code": 200,"code": "OK","message": f"Site '{site_name}' deleted successfully"}

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))



# ======================= Sites CRUD with tenant id hardcoded =============================================

TENANT_ID = "d4705477-cc27-4229-a0c3-04f55c3db721"

# create site
# async def create_site(request: Request, settings: Settings):
#     payload = await request.json()

#     if payload.get("operation") != "create" or payload.get("target") != "site":
#         return HttpStatusCode.BAD_REQUEST.response(message="Invalid request: operation must be 'create' and target must be 'site'")

#     entity = payload.get("entity") or {}
#     name = entity.get("name")
#     site_type = entity.get("type")
#     parent_name = entity.get("parentName")

#     if not name or not site_type or not parent_name:
#         return HttpStatusCode.BAD_REQUEST.response(message="Site 'name', 'type' and 'parentName' are required fields")

#     parent_project = await FRTUProjects.select(name=parent_name)
#     if not parent_project:
#         return HttpStatusCode.NOT_FOUND.response(message=f"Parent project '{parent_name}' not found")

#     existing = await FRTUSites.select(project_id=parent_project[0].id, name=name)
#     if existing:
#         return HttpStatusCode.BAD_REQUEST.response(message=f"Site with name '{name}' already exists in project '{parent_name}'")

#     exclude_keys = {"name", "type", "parentName"}
#     attributes = {k: v for k, v in entity.items() if k not in exclude_keys}
#     attributes["type"] = site_type

#     now = datetime.now(UTC).replace(tzinfo=None)

#     try:
#         value = await FRTUSites.insert(
#             project_id=parent_project[0].id,
#             name=name,
#             attribute=attributes,
#             creation_time=now,
#             last_update_time=now
#         )

#         response_data = {
#             "id": str(value.id),
#             "project_id": str(value.project_id),
#             "name": value.name,
#             "attribute": value.attribute,
#             "creation_time": value.creation_time.isoformat() if value.creation_time else None,
#             "last_update_time": value.last_update_time.isoformat() if value.last_update_time else None,
#         }

#         return HttpStatusCode.CREATED.response(message="FRTU Site created!", data=response_data)

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# get list of projects and get project by project name
# async def read_sites(request: Request):
#     payload = await request.json()
#     entity = payload.get("entity", {})
#     site_name = entity.get("name")
#     project_name = entity.get("projectName")  

#     if payload.get("operation") != "read" or payload.get("target") != "site":
#         return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

#     try:
#         filters = {}
        
#         if project_name:
#             parent_projects = await FRTUProjects.select(tenant_id=TENANT_ID, name=project_name)
#             if not parent_projects:
#                 return HttpStatusCode.NOT_FOUND.response(message=f"Project '{project_name}' not found", data=[])
#             filters["project_id"] = parent_projects[0].id

#         if site_name:
#             filters["name"] = site_name

#         if not filters:
#             parent_projects = await FRTUProjects.select(tenant_id=TENANT_ID)
#             if not parent_projects:
#                 return HttpStatusCode.NOT_FOUND.response(message="No projects found", data=[])
#             filters["project_id"] = [p.id for p in parent_projects]

#         sites = await FRTUSites.select(**filters)

#         if not sites:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Site '{site_name}' not found" if site_name else "No sites found",
#                 data=[]
#             )

#         response_data = []
#         for site in sites:
#             site_dict = dict(site)
#             attrs = site_dict.pop("attribute", {}) or {}
#             for k, v in attrs.items():
#                 site_dict[k] = v

#             parent_project = await FRTUProjects.select(id=site_dict.get("project_id"))
#             site_dict["parentName"] = parent_project[0].name if parent_project else None
#             site_dict.pop("project_id", None) 

#             if site_dict.get("creation_time"):
#                 site_dict["creation_time"] = site_dict["creation_time"].isoformat()
#             if site_dict.get("last_update_time"):
#                 site_dict["last_update_time"] = site_dict["last_update_time"].isoformat()
#             if site_dict.get("id"):
#                 site_dict["id"] = str(site_dict["id"])

#             response_data.append(site_dict)

#         if site_name:
#             response_data = response_data[0]

#         return HttpStatusCode.OK.response(
#             message=f"{len(sites)} site(s) fetched",
#             data=response_data
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# update project
# async def update_site(request: Request):
#     payload = await request.json()
    
#     if payload.get("operation") != "update" or payload.get("target") != "site":
#         return HttpStatusCode.BAD_REQUEST.response(
#             message="Invalid request: operation must be 'update' and target must be 'site'"
#         )

#     entity = payload.get("entity") or {}
#     site_name = entity.get("name")
    
#     if not site_name:
#         return HttpStatusCode.BAD_REQUEST.response(message="Site 'name' is required to update")

#     try:
#         site = await FRTUSites.select(name=site_name)
#         if not site:
#             return HttpStatusCode.NOT_FOUND.response(message=f"Site '{site_name}' not found")

#         site_obj = site[0]
#         exclude_keys = {"name", "type", "project_id"}
#         updated_attrs = {k: v for k, v in entity.items() if k not in exclude_keys}

#         existing_attrs = site_obj.attribute or {}
#         existing_attrs.update(updated_attrs)

#         now = datetime.now(UTC).replace(tzinfo=None)

#         await FRTUSites.update(
#             conditions={"name": site_name},
#             attribute=existing_attrs,
#             last_update_time=now
#         )

#         response_data = dict(site_obj)
#         response_data.pop("attribute", None)
#         response_data.update(existing_attrs)

#         from src.models.frtu_projects import FRTUProjects
#         parent_project = await FRTUProjects.select(id=site_obj.project_id)
#         response_data["parentName"] = parent_project[0].name if parent_project else None
#         response_data.pop("project_id", None)

#         if response_data.get("creation_time"):
#             response_data["creation_time"] = response_data["creation_time"].isoformat()
#         if response_data.get("last_update_time"):
#             response_data["last_update_time"] = response_data["last_update_time"].isoformat()
#         if response_data.get("id"):
#             response_data["id"] = str(response_data["id"])

#         return HttpStatusCode.OK.response(
#             message=f"Site '{site_name}' updated successfully",
#             data=response_data
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# delete project
# async def delete_site(request: Request):
#     payload = await request.json()
    
#     if payload.get("operation") != "delete" or payload.get("target") != "site":
#         return HttpStatusCode.BAD_REQUEST.response(
#             message="Invalid request: operation must be 'delete' and target must be 'site'"
#         )

#     entity = payload.get("entity") or {}
#     site_name = entity.get("name")

#     if not site_name:
#         return HttpStatusCode.BAD_REQUEST.response(message="Site 'name' is required to delete")

#     try:
#         site = await FRTUSites.select(name=site_name)
#         if not site:
#             return HttpStatusCode.NOT_FOUND.response(message=f"Site '{site_name}' not found")
        
#         site_id = site[0].id

#         devices = await FRTUDevices.select(site_id=site_id)
#         if devices:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message=f"Site '{site_name}' has {len(devices)} device(s). Delete them first."
#             )
#         await FRTUSites.delete(conditions={"name": site_name})

#         return HttpStatusCode.OK.response(message=f"Site '{site_name}' deleted successfully")

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

