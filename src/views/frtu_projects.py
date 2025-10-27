from datetime import UTC, datetime, timezone
import uuid
from zoneinfo import ZoneInfo
from click import UUID
from fastapi import HTTPException, Header, Request
from fastapi.responses import JSONResponse
from src.config.auth_config import ALGORITHM, SECRET_KEY
from src.models.frtu_sites import FRTUSites
from src.schemas.frtu_projects import FRTUProjectCreate, FRTUProjectRead, FRTUProjectUpdate
from src.models.frtu_projects import FRTUProjects
from src import Settings, HttpStatusCode
from src.utils.access_token import decode_token
from src.utils.schema import verify_schema
import jwt # type: ignore

TENANT_ID = "d4705477-cc27-4229-a0c3-04f55c3db721"

# ---------------- Create Project ----------------
async def create_project(request: Request, settings: Settings, authorization: str = Header(...)):
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
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

    payload = await request.json()
    if payload.get("operation") != "create" or payload.get("target") != "project":
        return HttpStatusCode.BAD_REQUEST.response(
            message="Invalid request: operation must be 'create' and target must be 'project'"
        )

    entity = payload.get("entity") or {}
    name = entity.get("name")
    proj_type = entity.get("type")

    if not name or not proj_type:
        return HttpStatusCode.BAD_REQUEST.response(
            message="name and type are required fields inside entity"
        )

    existing = await FRTUProjects.select(tenant_id=tenant_id, name=name)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response(
            message=f"Project with name '{name}' already exists for this tenant"
        )

    exclude_keys = {"name", "type"}
    attributes = {k: v for k, v in entity.items() if k not in exclude_keys}
    attributes["type"] = proj_type
    now = datetime.now(UTC).replace(tzinfo=None)

    try:
        value = await FRTUProjects.insert(
            tenant_id=tenant_id,
            name=name,
            attribute=attributes,
            creation_time=now,
            last_update_time=now
        )

        response_data = {
            "id": str(value.id),
            "tenant_id": str(value.tenant_id),
            "name": value.name,
            "attribute": value.attribute,
            "creation_time": value.creation_time.isoformat() if value.creation_time else None,
            "last_update_time": value.last_update_time.isoformat() if value.last_update_time else None,
        }

        return HttpStatusCode.CREATED.response(message="FRTU Project created!")

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# # ----------------- READ PROJECTS -----------------
async def read_projects(request: Request, authorization: str = Header(...)):
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return HttpStatusCode.response(HttpStatusCode.UNAUTHORIZED, "Invalid Authorization header")

    tenant_token = authorization.split(" ")[1]
    try:
        tenant_data = decode_token(tenant_token)
    except Exception as e:
        return HttpStatusCode.response(HttpStatusCode.UNAUTHORIZED, f"Tenant token decode failed: {str(e)}")

    tenant_id_str = tenant_data.get("tenant_id")
    if not tenant_id_str:
        return HttpStatusCode.response(HttpStatusCode.UNAUTHORIZED, "Invalid tenant token: tenant_id missing")

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except Exception as e:
        return HttpStatusCode.response(HttpStatusCode.BAD_REQUEST, f"Invalid tenant_id in token: {str(e)}")

    payload = await request.json()
    entity = payload.get("entity", {})
    project_name = entity.get("name")

    if payload.get("operation") != "read" or payload.get("target") != "project":
        return HttpStatusCode.response(HttpStatusCode.BAD_REQUEST, "Invalid operation or target")

    try:
        if project_name:
            projects = await FRTUProjects.select(tenant_id=tenant_id, name=project_name)
        else:
            projects = await FRTUProjects.select(tenant_id=tenant_id)

        if not projects:
            if project_name:
                return HttpStatusCode.NOT_FOUND.response(
                    message=f"Tenant does not have project '{project_name}'"
                )
            return JSONResponse(
                status_code=200,
                content={"count": 0, "projects": []}
            )

        response_data = []
        for proj in projects:
            proj_dict = dict(proj)

            attrs = proj_dict.pop("attribute", {}) or {}
            for k, v in attrs.items():
                proj_dict[k] = v

            if proj_dict.get("creation_time"):
                proj_dict["creationTs"] = int(proj_dict["creation_time"].timestamp() * 1000)
                proj_dict.pop("creation_time", None)
            if proj_dict.get("last_update_time"):
                proj_dict["lastUpdateTs"] = int(proj_dict["last_update_time"].timestamp() * 1000)
                proj_dict.pop("last_update_time", None)
            else:
                proj_dict["lastUpdateTs"] = None

            if proj_dict.get("id"):
                proj_dict["id"] = str(proj_dict["id"])
            if proj_dict.get("tenant_id"):
                proj_dict.pop("tenant_id", None)  

            sites = await FRTUSites.select(project_id=proj["id"])
            proj_dict["childNames"] = [site["name"] for site in sites] if sites else []

            response_data.append(proj_dict)

        if project_name:
            response_data = response_data[0]

        return JSONResponse(
            status_code=200,
            content={
                "count": len(projects),
                "projects": response_data if isinstance(response_data, list) else [response_data]
            }
        )

    except Exception as e:
        return HttpStatusCode.response(HttpStatusCode.BAD_REQUEST, str(e))


# # ----------------- UPDATE PROJECTS -----------------
async def update_project(request: Request, authorization: str = Header(...)):
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
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

    payload = await request.json()
    entity = payload.get("entity", {})
    project_name = entity.get("name")

    if payload.get("operation") != "update" or payload.get("target") != "project":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

    if not project_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Project 'name' is required")

    try:
        projects = await FRTUProjects.select(tenant_id=tenant_id, name=project_name)
        if not projects:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Tenant has no project named '{project_name}'"
            )

        project = projects[0]
        current_attrs = project["attribute"] or {}

        for k, v in entity.items():
            if k != "name":
                current_attrs[k] = v

        await FRTUProjects.update(
            conditions={"id": project["id"]},
            attribute=current_attrs,
            last_update_time=datetime.now(UTC).replace(tzinfo=None)
        )

        return HttpStatusCode.OK.response(message=f"Project '{project_name}' updated successfully")

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# # ----------------- DELETE PROJECTS -----------------
async def delete_project(request: Request, authorization: str = Header(...), settings: Settings = None):

    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
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
    project_name = entity.get("name")

    if payload.get("operation") != "delete" or payload.get("target") != "project":
        return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

    if not project_name:
        return HttpStatusCode.BAD_REQUEST.response(message="Project 'name' is required")

    try:
        project = await FRTUProjects.select(tenant_id=tenant_id, name=project_name)
        if not project:
            return HttpStatusCode.NOT_FOUND.response(message=f"Tenant has no project named '{project_name}'")

        project_id = project[0].id

        child_sites = await FRTUSites.select(project_id=project_id)
        if child_sites:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Project '{project_name}' has {len(child_sites)} site(s). Delete them first."
            )

        await FRTUProjects.delete(conditions={"tenant_id": tenant_id, "name": project_name})

        return {
            "http_code": 200,
            "code": "OK",
            "message": f"Project '{project_name}' deleted successfully"
        }

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))




# ----------------------- Project CRUD with hardcoded tenant id --------------------------------------
# async def create_project(request: Request, settings: Settings):
#     payload = await request.json()

#     if payload.get("operation") != "create" or payload.get("target") != "project":
#         return HttpStatusCode.BAD_REQUEST.response(
#             message="Invalid request: operation must be 'create' and target must be 'project'"
#         )

#     entity = payload.get("entity") or {}
#     name = entity.get("name")
#     proj_type = entity.get("type")

#     if not name or not proj_type:
#         return HttpStatusCode.BAD_REQUEST.response(
#             message="name and type are required fields inside entity"
#         )

#     existing = await FRTUProjects.select(tenant_id=TENANT_ID, name=name)
#     if existing:
#         return HttpStatusCode.BAD_REQUEST.response(
#             message=f"Project with name '{name}' already exists for this tenant"
#         )

#     exclude_keys = {"name", "type"}
#     attributes = {k: v for k, v in entity.items() if k not in exclude_keys}
#     attributes["type"] = proj_type

#     now = datetime.now(UTC).replace(tzinfo=None)

#     try:
#         value = await FRTUProjects.insert(
#             tenant_id=TENANT_ID,
#             name=name,
#             attribute=attributes,
#             creation_time=now,
#             last_update_time=now
#         )

#         response_data = {
#             "id": str(value.id),
#             "tenant_id": str(value.tenant_id),
#             "name": value.name,
#             "attribute": value.attribute,
#             "creation_time": value.creation_time.isoformat() if value.creation_time else None,
#             "last_update_time": value.last_update_time.isoformat() if value.last_update_time else None,
#         }

#         return HttpStatusCode.CREATED.response(message="FRTU Project created!", data=response_data)

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))  

# get list of projects/ project with children
# async def read_projects(request: Request):
#     payload = await request.json()
#     entity = payload.get("entity", {})
#     project_name = entity.get("name")

#     if payload.get("operation") != "read" or payload.get("target") != "project":
#         return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

#     try:
#         if project_name:
#             projects = await FRTUProjects.select(tenant_id=TENANT_ID, name=project_name)
#         else:
#             projects = await FRTUProjects.select(tenant_id=TENANT_ID)

#         if not projects:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Project '{project_name}' not found" if project_name else "No projects found",
#                 data=[]
#             )

#         response_data = []
#         for proj in projects:
#             proj_dict = dict(proj)

#             attrs = proj_dict.pop("attribute", {}) or {}
#             for k, v in attrs.items():
#                 proj_dict[k] = v

#             if proj_dict.get("creation_time"):
#                 proj_dict["creationTs"] = int(proj_dict["creation_time"].timestamp() * 1000)
#                 proj_dict.pop("creation_time", None)
#             if proj_dict.get("last_update_time"):
#                 proj_dict["lastUpdateTs"] = int(proj_dict["last_update_time"].timestamp() * 1000)
#                 proj_dict.pop("last_update_time", None)
#             else:
#                 proj_dict["lastUpdateTs"] = None

#             if proj_dict.get("id"):
#                 proj_dict["id"] = str(proj_dict["id"])
#             if proj_dict.get("tenant_id"):
#                 proj_dict["tenant_id"] = str(proj_dict["tenant_id"])

#             sites = await FRTUSites.select(project_id=proj["id"])
#             proj_dict["childNames"] = [site["name"] for site in sites] if sites else []

#             response_data.append(proj_dict)

#         if project_name:
#             response_data = response_data[0]

#         return HttpStatusCode.OK.response(
#             message=f"{len(projects)} project(s) fetched",
#             data=response_data
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# update project
# async def update_project(request: Request):
#     payload = await request.json()
#     entity = payload.get("entity", {})
#     project_name = entity.get("name")

#     if payload.get("operation") != "update" or payload.get("target") != "project":
#         return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

#     if not project_name:
#         return HttpStatusCode.BAD_REQUEST.response(message="Project 'name' is required")

#     try:
#         projects = await FRTUProjects.select(tenant_id=TENANT_ID, name=project_name)
#         if not projects:
#             return HttpStatusCode.BAD_REQUEST.response(message=f"Project '{project_name}' not found")
#         project = projects[0]

#         current_attrs = project["attribute"] or {}
#         for k, v in entity.items():
#             if k != "name":
#                 current_attrs[k] = v

#         await FRTUProjects.update(
#             conditions={"id": project["id"]},
#             attribute=current_attrs,
#             last_update_time=datetime.now(UTC).replace(tzinfo=None)
#         )

#         updated_project = await FRTUProjects.select(id=project["id"])
#         proj = updated_project[0]

#         proj_dict = dict(proj)
#         attrs = proj_dict.pop("attribute", {}) or {}
#         for k, v in attrs.items():
#             proj_dict[k] = v

#         if proj_dict.get("creation_time"):
#             proj_dict["creation_time"] = proj_dict["creation_time"].isoformat()
#         if proj_dict.get("last_update_time"):
#             proj_dict["last_update_time"] = proj_dict["last_update_time"].isoformat()

#         proj_dict["id"] = str(proj_dict["id"])
#         proj_dict["tenant_id"] = str(proj_dict["tenant_id"])

#         return HttpStatusCode.OK.response(message=f"Project '{project_name}' updated", data=proj_dict)
#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# delete project
# async def delete_project(request: Request):
#     payload = await request.json()
#     entity = payload.get("entity", {})
#     project_name = entity.get("name")

#     if payload.get("operation") != "delete" or payload.get("target") != "project":
#         return HttpStatusCode.BAD_REQUEST.response(message="Invalid operation or target")

#     if not project_name:
#         return HttpStatusCode.BAD_REQUEST.response(message="Project 'name' is required")

#     try:
#         project = await FRTUProjects.select(tenant_id=TENANT_ID, name=project_name)
#         if not project:
#             return HttpStatusCode.NOT_FOUND.response(
#                 message=f"Project '{project_name}' not found"
#             )
        
#         project_id = project[0].id

#         child_sites = await FRTUSites.select(project_id=project_id)
#         if child_sites:
#             return HttpStatusCode.BAD_REQUEST.response(
#                 message=f"Project '{project_name}' has {len(child_sites)} site(s). Delete them first."
#             )

#         await FRTUProjects.delete(conditions={"tenant_id": TENANT_ID, "name": project_name})
#         return HttpStatusCode.OK.response(
#             message=f"Project '{project_name}' deleted successfully"
#         )

#     except Exception as e:
#         return HttpStatusCode.BAD_REQUEST.response(message=str(e))





