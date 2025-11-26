from datetime import UTC, datetime, timezone
from math import ceil
import uuid
from uuid import UUID
from fastapi import Header, Request
from fastapi.responses import JSONResponse
from src.models.frtu_sites import FRTUSites
from src.models.frtu_tenants import FRTUTenants
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_projects import FRTUProjects
from src import Settings, HttpStatusCode
from src.schemas.frtu_projects import FRTUProjectDelete, FRTUProjectDeleteByID
from src.utils.access_token import decode_token
import jwt # type: ignore

async def create_project(data: dict, user_id: UUID):

    entity = data.get("entity", {})
    tenant_id: UUID = entity.get("tenant_id")
    name: str = entity.get("name")

    attribute = entity.copy()
    if "tenant_id" in attribute:
        del attribute["tenant_id"]

    for key, value in attribute.items():
        if isinstance(value, UUID):
            attribute[key] = str(value)

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.BAD_REQUEST.response("User not mapped to any Platform Admin")

    tenant_rows = await FRTUTenants.select(id=tenant_id)
    if not tenant_rows:
        return HttpStatusCode.NOT_FOUND.response("Invalid tenant_id")

    tenant = tenant_rows[0]

    if tenant.admin_id not in admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response(
            "You are not allowed to create a project under this tenant"
        )

    existing = await FRTUProjects.select(tenant_id=tenant_id, name=name)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response(
            f"Project '{name}' already exists under this tenant"
        )

    now = datetime.now(UTC).replace(tzinfo=None)

    project = await FRTUProjects.insert(
        tenant_id=tenant_id,
        name=name,
        attribute=attribute,
        creation_time=now,
        last_update_time=now
    )

    return HttpStatusCode.CREATED.response(
        message="Project created successfully",
        data={
            "project_id": str(project.id),
            "tenant_id": str(tenant_id),
            "name": name,
            "attribute": attribute
        }
    )



# # ----------------- READ PROJECTS -----------------
async def read_projects(
    user_id: UUID,
    tenant_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10
):
    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.BAD_REQUEST.response("User is not assigned to any Platform Admin")

    tenant_list = await FRTUTenants.select(admin_id=admin_ids)
    tenant_ids = [t.id for t in tenant_list]

    if tenant_id and tenant_id not in tenant_ids:
        return HttpStatusCode.ACCESS_DENIED.response("You are not allowed to access this tenant")

    valid_tenants = [tenant_id] if tenant_id else tenant_ids

    all_projects = []
    for t_id in valid_tenants:
        rows = await FRTUProjects.select(tenant_id=t_id)
        all_projects.extend(rows)

    if search:
        s = search.lower()

        exact = [p for p in all_projects if p.name.lower() == s]

        if exact:
            all_projects = exact
        else:
            all_projects = [p for p in all_projects if s in p.name.lower()]

    all_projects.sort(key=lambda p: p.last_update_time or datetime.min, reverse=True)

    total_records = len(all_projects)
    total_pages = ceil(total_records / limit) if limit > 0 else 1
    start = (page - 1) * limit
    end = start + limit
    page_records = all_projects[start:end]

    results = [
        {
            "project_id": str(p.id),
            "tenant_id": str(p.tenant_id),
            "name": p.name,
            "attribute": p.attribute
        }
        for p in page_records
    ]

    return HttpStatusCode.OK.response(
        message="Projects fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
            "projects": results
        }
    )


async def read_project_by_id(project_id: UUID, requester_id: UUID):

    assignments = await FRTUUserAssignment.select(user_id=requester_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response("User not assigned to any Platform Admin")

    project_list = await FRTUProjects.select(id=project_id)
    if not project_list:
        return HttpStatusCode.NOT_FOUND.response("Project not found")

    project = project_list[0]

    tenant = await FRTUTenants.select(id=project.tenant_id)
    if not tenant:
        return HttpStatusCode.NOT_FOUND.response("Tenant not found for this project")

    if tenant[0].admin_id not in admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response("You cannot access this project")

    return HttpStatusCode.OK.response(
        message="Project fetched successfully",
        data={
            "project_id": str(project.id),
            "tenant_id": str(project.tenant_id),
            "name": project.name,
            "attribute": project.attribute,
            "creation_time": str(project.creation_time),
            "last_update_time": str(project.last_update_time)
        }
    )


# # ----------------- UPDATE PROJECTS -----------------
async def update_project_by_name(data: dict, requester_id: UUID):

    entity = data.get("entity", {})
    project_name = entity.get("name")
    updates = entity.copy()
    updates.pop("name", None)

    if not project_name:
        return HttpStatusCode.BAD_REQUEST.response("Project name is required")

    assignments = await FRTUUserAssignment.select(user_id=requester_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response("User not mapped to any Platform Admin")

    tenant_list = await FRTUTenants.select(admin_id=admin_ids)
    tenant_ids = [t.id for t in tenant_list]

    if not tenant_ids:
        return HttpStatusCode.BAD_REQUEST.response("No tenant found under this user")

    projects = await FRTUProjects.select(name=project_name)
    if not projects:
        return HttpStatusCode.NOT_FOUND.response("Project not found with given name")

    target_project = None
    for p in projects:
        if p.tenant_id in tenant_ids:
            target_project = p
            break

    if not target_project:
        return HttpStatusCode.ACCESS_DENIED.response(
            "This project does not belong to your tenants"
        )

    project_id = target_project.id
    tenant_id = target_project.tenant_id
    current_attr = target_project.attribute or {}
    current_attr.update(updates)

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUProjects.update(
        conditions={"id": project_id},
        attribute=current_attr,
        last_update_time=now
    )

    return HttpStatusCode.OK.response(
        message="Project updated successfully",
        data={
            "project_id": str(project_id),
            "tenant_id": str(tenant_id),
            "name": project_name,
            "attribute": current_attr
        }
    )


async def update_project_by_id(project_id: UUID, data: dict, user_id: UUID):

    entity = data.get("entity", {})
    updates = entity.copy()

    project_rows = await FRTUProjects.select(id=project_id)
    if not project_rows:
        return HttpStatusCode.NOT_FOUND.response("Project not found")

    project = project_rows[0]

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response("User not mapped to any Platform Admin")

    tenant_list = await FRTUTenants.select(admin_id=admin_ids)
    tenant_ids = [t.id for t in tenant_list]

    if project.tenant_id not in tenant_ids:
        return HttpStatusCode.ACCESS_DENIED.response("You are not allowed to update this project")

    tenant_id = project.tenant_id
    project_name = project.name
    current_attr = project.attribute or {}

    current_attr.update(updates)

    now = datetime.now(UTC).replace(tzinfo=None)

    await FRTUProjects.update(
        conditions={"id": project_id},
        attribute=current_attr,
        last_update_time=now
    )

    return HttpStatusCode.OK.response(
        message="Project updated successfully",
        data={
            "project_id": str(project_id),
            "tenant_id": str(tenant_id),
            "name": project_name,
            "attribute": current_attr
        }
    )


# # ----------------- DELETE PROJECTS -----------------
async def delete_project_by_name(data: FRTUProjectDelete, user_id: UUID):

    project_name = data.entity["name"]

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response("User is not assigned to any Platform Admin")

    tenant_list = await FRTUTenants.select(admin_id=admin_ids)
    if not tenant_list:
        return HttpStatusCode.BAD_REQUEST.response("No tenant available under this user")

    tenant_id = tenant_list[0].id

    project_rows = await FRTUProjects.select(tenant_id=tenant_id, name=project_name)
    if not project_rows:
        return HttpStatusCode.NOT_FOUND.response(f"Project '{project_name}' not found")

    project = project_rows[0]

    children = await FRTUSites.select(project_id=project.id)
    if children:
        return HttpStatusCode.BAD_REQUEST.response({
            "title": "Cannot Delete Project",
            "message": f"Project '{project_name}' has Sites assigned. Delete sites first.",
            "action_required": "delete_sites_first"
        })

    try:
        await FRTUProjects.delete(conditions={"id": project.id})

        return HttpStatusCode.OK.response(
            message="Project deleted successfully",
            data={"project_id": str(project.id), "name": project_name}
        )

    except Exception as e:
        return HttpStatusCode.SERVER_ERROR.response(str(e))


async def delete_project_by_id(data: FRTUProjectDeleteByID, user_id: UUID):

    project_id = UUID(data.entity["id"])

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.ACCESS_DENIED.response("User is not assigned to any Platform Admin")

    tenant_list = await FRTUTenants.select(admin_id=admin_ids)
    if not tenant_list:
        return HttpStatusCode.BAD_REQUEST.response("No tenant available under this user")

    tenant_id = tenant_list[0].id

    project_rows = await FRTUProjects.select(id=project_id, tenant_id=tenant_id)
    if not project_rows:
        return HttpStatusCode.NOT_FOUND.response("Project not found under this tenant")

    project = project_rows[0]

    children = await FRTUSites.select(project_id=project_id)
    if children:
        return HttpStatusCode.BAD_REQUEST.response({
            "title": "Cannot Delete Project",
            "message": "Delete all sites under this project first",
            "action_required": "delete_sites_first"
        })

    try:
        await FRTUProjects.delete(conditions={"id": project_id})

        return HttpStatusCode.OK.response(
            message="Project deleted successfully",
            data={"project_id": str(project_id)}
        )

    except Exception as e:
        return HttpStatusCode.SERVER_ERROR.response(str(e))
