import secrets
from click import UUID
from fastapi import HTTPException, Header, Request
from src.core.settings import Settings
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_projects import FRTUProjects
from src.models.frtu_tenants import FRTUTenants
from src.schemas.frtu_tenants import FRTUTenantCreate, FRTUTenantRead
from src import  HttpStatusCode
from datetime import datetime, UTC, timedelta
from src.utils.schema import verify_schema
from fastapi import Request, Header, HTTPException, Depends
import jwt
from src.config.auth_config import SECRET_KEY, ALGORITHM


# create tenant under specific admin
async def create_tenant(request: Request, settings: Settings):
    try:
        admin_name = request.query_params.get("admin_name")
        if not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing admin_name in query params"
            )

        payload = await request.json()
        name = payload.get("name")
        if not name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Tenant 'name' is required in payload"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )

        admin_id = admin[0]["id"]

        existing = await FRTUTenants.select(admin_id=admin_id, name=name)
        if existing:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Tenant '{name}' already exists for admin '{admin_name}'"
            )

        attributes = {k: v for k, v in payload.items() if k != "name"}

        now = datetime.now(UTC).replace(tzinfo=None)

        value = await FRTUTenants.insert(
            admin_id=admin_id,
            name=name,
            attribute=attributes,
            creation_time=now,
            last_update_time=now
        )

        response_data = {
            "id": str(value.id),
            "admin_id": str(value.admin_id),
            "name": value.name,
            "attribute": value.attribute,
            "creation_time": value.creation_time.isoformat() if value.creation_time else None,
            "last_update_time": value.last_update_time.isoformat() if value.last_update_time else None,
        }

        return HttpStatusCode.CREATED.response(
            message="Tenant created successfully",
            data=response_data
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# get list of all tenant under specific admin
async def get_tenants(request: Request):
    try:
        admin_name = request.query_params.get("admin_name")
        if not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing admin_name in query params"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )

        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"No tenants found for admin '{admin_name}'"
            )

        response_data = []
        for tenant in tenants:
            tenant_dict = dict(tenant)
            if tenant_dict.get("creation_time"):
                tenant_dict["creation_time"] = tenant_dict["creation_time"].isoformat()
            if tenant_dict.get("last_update_time"):
                tenant_dict["last_update_time"] = tenant_dict["last_update_time"].isoformat()

            if tenant_dict.get("id"):
                tenant_dict["id"] = str(tenant_dict["id"])
            if tenant_dict.get("admin_id"):
                tenant_dict["admin_id"] = str(tenant_dict["admin_id"])

            response_data.append(tenant_dict)

        return HttpStatusCode.OK.response(
            message=f"{len(response_data)} tenant(s) fetched for admin '{admin_name}'",
            data=response_data
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# get specific tenant( by tenant name ) under specific admin
async def get_tenant_by_name(request: Request):
    try:
        admin_name = request.query_params.get("admin_name")
        tenant_name = request.query_params.get("tenant_name")

        if not admin_name or not tenant_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing required query params: admin_name and tenant_name"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )

        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Tenant '{tenant_name}' not found for admin '{admin_name}'"
            )

        tenant = dict(tenants[0])

        if tenant.get("id"):
            tenant["id"] = str(tenant["id"])
        if tenant.get("admin_id"):
            tenant["admin_id"] = str(tenant["admin_id"])
        if tenant.get("creation_time"):
            tenant["creation_time"] = tenant["creation_time"].isoformat()
        if tenant.get("last_update_time"):
            tenant["last_update_time"] = tenant["last_update_time"].isoformat()

        return HttpStatusCode.OK.response(
            message=f"Tenant '{tenant_name}' fetched for admin '{admin_name}'",
            data=tenant
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# update tenant detail for specific admin
async def update_tenant(request: Request):
    try:
        tenant_name = request.query_params.get("tenant_name")
        admin_name = request.query_params.get("admin_name")

        if not tenant_name or not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing 'tenant_name' or 'admin_name' in query params"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )
        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Tenant '{tenant_name}' not found for admin '{admin_name}'"
            )
        tenant_id = tenants[0]["id"]

        payload = await request.json()
        updated_attributes = payload or tenants[0]["attribute"] or {}
        # now = datetime.now(UTC)
        now = datetime.utcnow()

        await FRTUTenants.update(
            conditions={"id": tenant_id},
            attribute=updated_attributes,
            last_update_time=now
        )

        updated_tenant = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        tenant_dict = dict(updated_tenant[0])
        tenant_dict["id"] = str(tenant_dict["id"])
        tenant_dict["admin_id"] = str(tenant_dict["admin_id"])
        tenant_dict["creation_time"] = tenant_dict["creation_time"].isoformat()
        tenant_dict["last_update_time"] = tenant_dict["last_update_time"].isoformat()

        return HttpStatusCode.OK.response(
            message=f"Tenant '{tenant_name}' updated successfully",
            data=tenant_dict
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))

# delete tenant of specific admin
async def delete_tenant(request: Request):
    try:
        tenant_name = request.query_params.get("tenant_name")
        admin_name = request.query_params.get("admin_name")

        if not tenant_name or not admin_name:
            return HttpStatusCode.BAD_REQUEST.response(
                message="Missing 'tenant_name' or 'admin_name' in query params"
            )

        admin = await FRTUPlatformAdmin.select(name=admin_name)
        if not admin:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Admin '{admin_name}' not found"
            )
        admin_id = admin[0]["id"]

        tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
        if not tenants:
            return HttpStatusCode.NOT_FOUND.response(
                message=f"Tenant '{tenant_name}' not found for admin '{admin_name}'"
            )
        tenant_id = tenants[0]["id"]

        projects = await FRTUProjects.select(tenant_id=tenant_id)
        if projects:
            return HttpStatusCode.BAD_REQUEST.response(
                message=f"Tenant '{tenant_name}' cannot be deleted because it has projects"
            )

        await FRTUTenants.delete(conditions={"id": tenant_id})

        return HttpStatusCode.OK.response(
            message=f"Tenant '{tenant_name}' deleted successfully"
        )

    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


# tenant_auth.py
def create_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

async def tenant_login(request: Request, authorization: str = Header(...)):
    payload = await request.json()
    tenant_name = payload.get("name")
    if not tenant_name:
        raise HTTPException(status_code=400, detail="Tenant name required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.split(" ")[1]

    try:
        admin_data = decode_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token decode failed: {str(e)}")

    admin_id_str = admin_data.get("admin_id")
    admin_id = UUID(admin_id_str)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    tenants = await FRTUTenants.select(admin_id=admin_id, name=tenant_name)
    if not tenants:
        raise HTTPException(status_code=403, detail=f"Admin does not have tenant '{tenant_name}'")

    tenant_id = str(tenants[0]["id"])
    tenant_token = create_token({"tenant_id": tenant_id, "tenant_name": tenant_name})
    return {"tenant_token": tenant_token, "tenant_id": tenant_id, "name": tenant_name}




