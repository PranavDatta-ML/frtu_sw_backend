from copy import deepcopy
from datetime import UTC, datetime
from math import ceil
from fastapi import HTTPException
from src.core.status_codes import HttpStatusCode
from src.models.frtu_entities import FRTUEntities
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_roles import FRTURoles
from src.models.frtu_tenants import FRTUTenants
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers
from src.schemas.frtu_tenants import FRTUTenantCreate, FRTUTenantOut, FRTUTenantUpdate
from uuid import UUID

async def get_projects_for_tenant(tenant_id: UUID):
    project_list = await FRTUProjects.select(tenant_id=tenant_id)
    return [
        {
            "project_id": str(p.id),
            "project_name": p.name,
            "attribute": p.attribute or {}
        }
        for p in project_list
    ]

async def create_tenant(data: FRTUTenantCreate, user_id: UUID):

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    if not assignments:
        return HttpStatusCode.BAD_REQUEST.response("User is not assigned to any Platform Admin")

    admin_id = assignments[0].admin_id
    if not admin_id:
        return HttpStatusCode.BAD_REQUEST.response("No Platform Admin associated with this user")

    existing = await FRTUTenants.select(admin_id=admin_id, name=data.name)
    if existing:
        return HttpStatusCode.BAD_REQUEST.response(
            f"Tenant '{data.name}' already exists under this admin"
        )

    now = datetime.utcnow()

    attribute_data = data.attribute or {}
    attribute_data["email"] = data.email if data.email else None
    attribute_data["mobile_no"] = data.mobile_no if data.mobile_no else None

    tenant = await FRTUTenants.insert(
        admin_id=admin_id,
        name=data.name,
        attribute=attribute_data,
        creation_time=now,
        last_update_time=now
    )

    await FRTUEntities.insert(
        entity_id=tenant.id,
        name=data.name,
        email_id=data.email if data.email else None,
        mobile_no=data.mobile_no if data.mobile_no else None,
        attribute=attribute_data,
        created_by=user_id,
        creation_time=now,
        last_update_time=now
    )

    out = FRTUTenantOut(
        id=tenant.id,
        admin_id=admin_id,
        created_by=user_id,
        name=data.name,
        attribute=attribute_data
    )

    return HttpStatusCode.CREATED.response(
        message="Tenant created successfully",
        data=out.model_dump(mode="json")
    )


# get tenant by id
async def get_tenant_by_id(tenant_id: UUID, user_id: UUID):

    tenant_list = await FRTUTenants.select(id=tenant_id)
    if not tenant_list:
        return HttpStatusCode.NOT_FOUND.response("Tenant not found")

    tenant = tenant_list[0]

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.BAD_REQUEST.response("User is not assigned to any Platform Admin")

    if tenant.admin_id not in admin_ids:
        return HttpStatusCode.BAD_REQUEST.response("You cannot view this tenant")

    admin_list = await FRTUPlatformAdmin.select(id=tenant.admin_id)
    admin = admin_list[0] if admin_list else None

    entity_list = await FRTUEntities.select(entity_id=tenant_id)
    entity = entity_list[0] if entity_list else None
    projects = await get_projects_for_tenant(tenant_id)
    data = {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "attribute": tenant.attribute,
        "admin_id": str(tenant.admin_id),
        "admin_name": admin.name if admin else None,
        # "admin_created_by": str(admin.created_by) if admin and admin.created_by else None,
        "email": entity.email_id if entity else None,
        "mobile_no": entity.mobile_no if entity else None,
        "children": {"projects": projects}
    }

    return HttpStatusCode.OK.response(
        message="Tenant fetched successfully",
        data=data
    )


async def get_tenants(user_id: UUID, name: str | None = None, search: str | None = None, page: int = 1, limit: int = 10):
    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]
    if not admin_ids:
        return HttpStatusCode.OK.response(
            message="No platform admin assigned",
            data={"page": page, "limit": limit, "total_records": 0, "total_pages": 0, "tenants": []}
        )

    tenants = []
    for admin_id in admin_ids:
        tenants_for_admin = await FRTUTenants.select(admin_id=admin_id)
        tenants.extend(tenants_for_admin)

    if name:
        name_lower = name.lower()

        exact_matches = [t for t in tenants if t.name.lower() == name_lower]

        if exact_matches:
            filtered_tenants = exact_matches
        else:
            filtered_tenants = [t for t in tenants if name_lower in t.name.lower()]
    else:
        filtered_tenants = tenants
    
    filtered_tenants.sort(
        key=lambda t: (
            t.last_update_time or datetime.min,
            t.creation_time or datetime.min
        ),
        reverse=True
    )

    total_records = len(filtered_tenants)
    total_pages = ceil(total_records / limit) if limit > 0 else 1
    start = (page - 1) * limit
    end = start + limit if limit > 0 else total_records
    paginated = filtered_tenants[start:end]

    tenant_list = [
        {
            "tenant_id": str(t.id),
            "tenant_name": t.name,
            "attribute": t.attribute or {},
            "admin_id": str(t.admin_id),
            "projects": await get_projects_for_tenant(t.id)
        }
        for t in paginated
    ]

    return HttpStatusCode.OK.response(
        message="Tenants fetched successfully",
        data={
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
            "tenants": tenant_list
        }
    )


async def update_tenant(tenant_id: UUID, data: dict, user_id: UUID):

    tenant_list = await FRTUTenants.select(id=tenant_id)
    if not tenant_list:
        return HttpStatusCode.NOT_FOUND.response("Tenant not found")

    tenant = tenant_list[0]

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.BAD_REQUEST.response("User is not assigned to any Platform Admin")

    if tenant.admin_id not in admin_ids:
        return HttpStatusCode.BAD_REQUEST.response("You are not allowed to update this tenant")

    new_name = data.get("name", tenant.name)

    current_attr = tenant.attribute or {}
    new_attr = current_attr.copy()

    if data.get("attribute"):
        new_attr.update(data["attribute"])

    now = datetime.utcnow()

    await FRTUTenants.update(
        conditions={"id": tenant_id},
        name=new_name,
        attribute=new_attr,
        last_update_time=now
    )

    entity_list = await FRTUEntities.select(entity_id=tenant_id)
    if entity_list:
        entity = entity_list[0]

        email = new_attr.get("email", entity.email_id)
        mobile = new_attr.get("mobile_no", entity.mobile_no)

        await FRTUEntities.update(
            conditions={"entity_id": tenant_id},
            name=new_name,
            email_id=email,
            mobile_no=mobile,
            attribute=new_attr,
            last_update_time=now
        )

    return HttpStatusCode.OK.response(
        message="Tenant updated successfully",
        data={
            "tenant_id": str(tenant_id),
            "name": new_name,
            "attribute": new_attr
        }
    )


async def delete_tenant(tenant_id: UUID, user_id: UUID, is_deleted: bool = False):

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    admin_ids = [a.admin_id for a in assignments if a.admin_id]

    if not admin_ids:
        return HttpStatusCode.BAD_REQUEST.response(
            "User is not assigned to any Platform Admin"
        )

    tenant_rows = await FRTUTenants.select(id=tenant_id)
    if not tenant_rows:
        return HttpStatusCode.NOT_FOUND.response("Tenant not found")

    tenant = tenant_rows[0]

    if tenant.admin_id not in admin_ids:
        return HttpStatusCode.BAD_REQUEST.response(
            "You are not allowed to delete this tenant"
        )

    projects = await FRTUProjects.select(tenant_id=tenant_id)

    if projects:
        return HttpStatusCode.OK.response({
            "title": "Cannot Delete Tenant",
            "message": "You cannot delete this Tenant until all associated Projects are deleted.",
            "action_required": "delete_projects_first",
            "is_deleted": False
        })
    if not is_deleted:
        return {
            "http_code": 200,
            "code": "CONFIRM_REQUIRED",
            "message": {
                "title": "Confirm Tenant Deletion",
                "message": "Are you sure you want to delete this tenant?",
                "action_required": "set_is_deleted_true",
                "is_deleted_required": True,
                "is_deleted": True
            }
        }

    try:
        await FRTUTenants.delete(conditions={"id": tenant_id})
        await FRTUEntities.delete(conditions={"entity_id": tenant_id})

        # return HttpStatusCode.OK.response(
        #     message="Tenant deleted successfully",
        #     data={"tenant_id": str(tenant_id)},
        #     is_deleted=is_deleted
        # )
        return {
            "http_code": 200,
            "code": "SUCCESS",
            "message": {"message": "Tenant deleted successfully", "tenant_id": str(tenant_id),"is_deleted": True},   
        }
    except Exception as e:
        return HttpStatusCode.INTERNAL_SERVER_ERROR.response(str(e))

