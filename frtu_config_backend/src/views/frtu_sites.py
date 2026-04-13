from datetime import UTC, datetime
from typing import Any, Dict
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, Header, Request
from src.config.auth_config import ALGORITHM, SECRET_KEY
from src.enums.FrtuDeviceType import FrtuDeviceType
from src.models.frtu_devices import FRTUDevices
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.schemas.frtu_projects import FRTUProjectCreate
from src.models.frtu_sites import FRTUSites
from src.models.frtu_projects import FRTUProjects
from src import Settings, HttpStatusCode
from src.utils.access_token import decode_token

def safe_get(data, key, default=""):
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


# ---------------- Create Site ----------------
async def create_site(data: dict, user_id: UUID):

    entity = data.get("entity", {})
    name = entity.get("name")
    
    if not name:
        return HttpStatusCode.BAD_REQUEST.response("Site name is required")
    
    project_id = entity.get("project_id")
    if not project_id:
        return HttpStatusCode.BAD_REQUEST.response("project_id is required")
    
    try:
        project_id = UUID(entity.get("project_id"))
    except:
        return HttpStatusCode.BAD_REQUEST.response("Invalid project_id format. Must be UUID.")

    project_rows = await FRTUProjects.select(id=project_id)
    if not project_rows:
        return HttpStatusCode.NOT_FOUND.response("Project not found")

    project_row = project_rows[0]

    # build a plain dict using known columns; no lazy loading later
    target_project = {
        "id": str(project_row.id),
        "name": project_row.name,        # or project_row.project_name
        # add any other needed columns explicitly
    }

    # assignments = await FRTUUserAssignment.select(user_id=user_id)
    # allowed_tenants = [a.scope_id for a in assignments if a.scope_type == "TENANT"]

    # if target_project.tenant_id not in allowed_tenants:
    #     return HttpStatusCode.ACCESS_DENIED.response("You are not allowed to create site under this project")

    device_type = entity.get("device_type")
    if device_type:
        try:
            device_type = FrtuDeviceType(device_type).value
        except Exception:
            return HttpStatusCode.BAD_REQUEST.response(
                "Invalid device_type. Allowed values: FRTU, RTU"
            )

    attribute = entity.copy()
    attribute["device_type"] = device_type

    now = datetime.now(UTC).replace(tzinfo=None)

    existing = await FRTUSites.select(project_id=project_id, name=name)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response("Site already exists under this project")

    site = await FRTUSites.insert(
        project_id=project_id,
        name=name,
        attribute=attribute,
        creation_time=now,
        last_update_time=now
    )

    merged_data = {
        "id": str(site.id),
        "project_id": str(project_id),
        "name": site.name,
        "device_type": device_type,
        "project_name": target_project["name"],
        "creation_time": site.creation_time.isoformat() if site.creation_time else None,
        "last_update_time": site.last_update_time.isoformat() if site.last_update_time else None,
    }   

    merged_data.update(attribute)

    return HttpStatusCode.CREATED.response(
        message="Site created successfully",
        data=merged_data,
    )


# ---------------- Read Sites ---------------- 
async def read_sites(data: dict, requester_id: UUID, name: str | None, page: int, limit: int):

    entity = data.get("entity") or {}
    payload_name = entity.get("name") if isinstance(entity, dict) else None
    final_search = payload_name or name or None

    all_rows = await FRTUSites.select()
    site_list = []

    for row in all_rows:
        project_row = None
        project_rows = await FRTUProjects.select(id=row.project_id)
        if project_rows:
            project_row = project_rows[0]

        attr = row.attribute or {}

        site_list.append({
            "id": str(row.id),
            "name": row.name,
            "type": "site",
            "label": attr.get("label"),
            "description": attr.get("description"),
            "creationTs": int(row.creation_time.timestamp()*1000) if row.creation_time else None,
            "lastUpdateTs": int(row.last_update_time.timestamp()*1000) if row.last_update_time else None,
            "parentName": project_row.name if project_row else "",
            "project_name": project_row.name if project_row else "",
            "project_id": str(row.project_id),
            "latitude": attr.get("latitude"),
            "longitude": attr.get("longitude"),
            "status": attr.get("status"),
            "deviceType": attr.get("device_type"),
        })

    if final_search:
        final_search = final_search.lower()
        site_list = [s for s in site_list if final_search in s["name"].lower()]

    total_records = len(site_list)
    total_pages = (total_records + limit - 1) // limit

    start = (page - 1) * limit
    end = start + limit
    paginated_sites = site_list[start:end]

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Sites fetched successfully",
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "total_pages": total_pages,
        "sites": paginated_sites
    }


# ---------------- Read Site By ID ----------------
async def read_site_by_id(site_id: UUID, requester_id: UUID, data: dict):
    rows = await FRTUSites.select(id=site_id)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Site not found")

    row = rows[0]
    attr = row.attribute or {}

    parent_name = ""
    project_name = ""
    project_rows = await FRTUProjects.select(id=row.project_id)

    if project_rows:
        project = project_rows[0]
        project_name = project.name
        parent_name = project.name

    site_obj = {
        "id": str(row.id),
        "name": row.name,
        "type": "site",
        "label": attr.get("label"),
        "description": attr.get("description"),

        "creationTs": int(row.creation_time.timestamp() * 1000)
        if row.creation_time else None,

        "lastUpdateTs": int(row.last_update_time.timestamp() * 1000)
        if row.last_update_time else None,

        "parentName": parent_name,
        "project_name": project_name,
        "project_id": str(row.project_id),

        "latitude": attr.get("latitude"),
        "longitude": attr.get("longitude"),
        "status": attr.get("status"),
        "deviceType": attr.get("device_type"),
    }

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Site fetched successfully",
        "count": 1,
        "sites": [site_obj]
    }


# ---------------- Update Site By Name ----------------
async def update_site_by_name(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}
    site_name = entity.get("name")
    if not site_name:
        return HttpStatusCode.BAD_REQUEST.response("Site name is required")

    rows = await FRTUSites.select(name=site_name)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Site not found")

    orm = rows[0]
    row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}

    row_id = row["id"]
    project_id = row["project_id"]
    existing_attr = row.get("attribute") or {}

    updated_attr = existing_attr.copy()
    for key, value in entity.items():
        if key != "name" and value is not None:
            updated_attr[key] = value

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUSites.update(
        conditions={"id": row_id},
        attribute=updated_attr,
        last_update_time=now
    )

    project_rows = await FRTUProjects.select(id=project_id)
    project_name = ""
    if project_rows:
        project = project_rows[0]
        project_data = {c.name: getattr(project, c.name) for c in project.__table__.columns}
        project_name = project_data.get("name", "")

    return HttpStatusCode.OK.response(
        message="Site updated successfully",
        data={
            "id": str(row_id),
            "name": row["name"],
            "project_id": str(project_id),
            "project_name": project_name,
            "creationTs": int(row["creation_time"].timestamp() * 1000) if row.get("creation_time") else None,
            "lastUpdateTs": int(now.timestamp() * 1000),
            "attribute": updated_attr
        }
    )



async def update_site_by_id(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}

    raw_id = entity.get("id")
    if not raw_id:
        return HttpStatusCode.BAD_REQUEST.response("Site ID is required")

    site_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))

    rows = await FRTUSites.select(id=site_id)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Site not found")

    orm = rows[0]
    row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}

    project_id = row["project_id"]
    existing_attr = row.get("attribute") or {}
    updated_attr = existing_attr.copy()

    updated_name = row["name"]

    for key, value in entity.items():
        if key == "name" and value:
            updated_name = value
        elif key != "id" and value is not None:
            updated_attr[key] = value

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUSites.update(
        conditions={"id": site_id},
        name=updated_name,
        attribute=updated_attr,
        last_update_time=now
    )

    project_rows = await FRTUProjects.select(id=project_id)
    project_name = ""
    if project_rows:
        project = project_rows[0]
        project_dict = {c.name: getattr(project, c.name) for c in project.__table__.columns}
        project_name = project_dict.get("name", "")

    return HttpStatusCode.OK.response(
        message="Site updated successfully",
        data={
            "id": str(site_id),
            "name": updated_name,
            "project_id": str(project_id),
            "project_name": project_name,
            "creationTs": int(row["creation_time"].timestamp() * 1000) if row.get("creation_time") else None,
            "lastUpdateTs": int(now.timestamp() * 1000),
            "attribute": updated_attr
        }
    )
  

# ---------------- Update Site By Name or ID----------------
async def update_site(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}

    raw_id = entity.get("id")
    site_name = entity.get("name")
    if raw_id:
        try:
            site_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        except:
            return HttpStatusCode.BAD_REQUEST.response("Invalid site ID format")

        rows = await FRTUSites.select(id=site_id)
        if not rows:
            return HttpStatusCode.NOT_FOUND.response("Site not found")
        orm = rows[0]

    else:
        if not site_name:
            return HttpStatusCode.BAD_REQUEST.response("Either site ID or site name is required")

        rows = await FRTUSites.select(name=site_name)
        if not rows:
            return HttpStatusCode.NOT_FOUND.response("Site not found")
        orm = rows[0]
        site_id = getattr(orm, "id")

    row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}

    updated_name = row["name"]
    project_id = row["project_id"]
    existing_attr = row.get("attribute") or {}
    updated_attr = existing_attr.copy()

    for key, value in entity.items():
        if key == "name" and value:
            updated_name = value
        elif key not in ("id",) and value is not None:
            updated_attr[key] = value

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUSites.update(
        conditions={"id": site_id},
        name=updated_name,
        attribute=updated_attr,
        last_update_time=now
    )

    project_rows = await FRTUProjects.select(id=project_id)
    project_name = ""
    if project_rows:
        project = project_rows[0]
        project_dict = {c.name: getattr(project, c.name) for c in project.__table__.columns}
        project_name = project_dict.get("name", "")

    return HttpStatusCode.OK.response(
        message="Site updated successfully",
        data={
            "id": str(site_id),
            "name": updated_name,
            "project_id": str(project_id),
            "project_name": project_name,
            "creationTs": int(row["creation_time"].timestamp() * 1000) if row.get("creation_time") else None,
            "lastUpdateTs": int(now.timestamp() * 1000),
            "attribute": updated_attr
        }
    )


# ---------------- Delete Site ----------------
async def delete_site_by_name(data: dict, requester_id: UUID):

    entity = data.get("entity") or {}
    site_name = entity.get("name")

    if not site_name:
        return HttpStatusCode.BAD_REQUEST.response("Site name is required")

    rows = await FRTUSites.select(name=site_name)
    if not rows:
        return HttpStatusCode.NOT_FOUND.response("Site not found")

    orm = rows[0]
    row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}
    site_id = row["id"]

    device_rows = await FRTUDevices.select(site_id=site_id)
    if device_rows:
        return HttpStatusCode.BAD_REQUEST.response(
            f"Cannot delete site '{site_name}'. Devices exist under this site."
        )

    await FRTUSites.delete(conditions={"id": site_id})

    return HttpStatusCode.OK.response(
        message=f"Site '{site_name}' deleted successfully",
        data={"deleted_site_id": str(site_id)}
    )


async def delete_site(data: Dict[str, Any], requester_id: UUID, confirm_delete: bool):
    entity = data.get("entity") or {}
    raw_id = entity.get("id")
    site_name = entity.get("name")

    if raw_id:
        try:
            site_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        except Exception:
            return HttpStatusCode.BAD_REQUEST.response("Invalid site ID format")

        rows = await FRTUSites.select(id=site_id)
        if not rows:
            return HttpStatusCode.NOT_FOUND.response("Site not found")

        orm = rows[0]
        row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}
        site_name = row.get("name", "")
    else:
        if not site_name:
            return HttpStatusCode.BAD_REQUEST.response("Either site ID or site name is required")

        rows = await FRTUSites.select(name=site_name)
        if not rows:
            return HttpStatusCode.NOT_FOUND.response("Site not found")

        orm = rows[0]
        row = {c.name: getattr(orm, c.name) for c in orm.__table__.columns}
        site_id = row["id"]

    device_rows = await FRTUDevices.select(site_id=site_id)
    if device_rows:
        return HttpStatusCode.OK.response(
            {
                "message": f"Cannot delete site '{site_name}'. Devices exist under this site.",
                "action_required": "delete_devices_first",
                "is_deleted": False,

            }
        )

    if not confirm_delete:
        return HttpStatusCode.OK.response({
            "message": f"Site '{site_name}' has no devices; deletion not confirmed",
            "is_deleted": True
        })

    await FRTUSites.delete(conditions={"id": site_id})

    return HttpStatusCode.OK.response({
        "message": f"Site '{site_name}' deleted successfully",
        "is_deleted": True
    })

