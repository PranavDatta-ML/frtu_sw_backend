from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from uuid import UUID

from src.core.status_codes import HttpStatusCode
from src.schemas.frtu_tenants import FRTUTenantCreate, FRTUTenantOut, FRTUTenantUpdate, FRTUTenantRead
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_tenants import create_tenant, get_tenant_by_id, get_tenants, update_tenant, delete_tenant
from src.middleware.CreatePermissionMiddleware import require_permission

router = APIRouter(
    prefix="/api/tenants",
    tags=["frtu_tenants"]
)

# CREATE
@router.post("")
async def api_create_tenant(
    data: FRTUTenantCreate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "TENANT"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    creator_id = UUID(decoded["sub"])
    return await create_tenant(data, creator_id)


# get tenant by id
@router.get("/{tenant_id}")
async def api_get_tenant_by_id(
    tenant_id: UUID,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "TENANT"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await get_tenant_by_id(tenant_id, requester_id)



# GET ALL Tenants/ Get specific Tenant and search
@router.get("/")
async def api_get_tenants(
    name: str | None = Query(None),
    page: int = Query(1),
    limit: int = Query(10),
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "TENANT"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await get_tenants(user_id=requester_id, name=name, page=page, limit=limit)


# UPDATE
@router.put("/{tenant_id}")
async def api_update_tenant(
    tenant_id: UUID,
    data: FRTUTenantUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "TENANT"))
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_tenant(tenant_id, data.model_dump(), requester_id)



# DELETE
# @router.delete("/{tenant_id}")
# async def api_delete_tenant(
#     tenant_id: UUID,
#     authorization: str = Header(...),
#     user_id: UUID = Depends(require_permission("edit", "TENANT"))
# ):
#     token = authorization.split(" ")[1]
#     decoded = decode_access_token(token)
#     requester_id = UUID(decoded["sub"])
#     return await delete_tenant(tenant_id, requester_id)


@router.delete("/{tenant_id}")
async def api_delete_tenant(
    tenant_id: UUID,
    is_deleted: bool = Query(False),   # <-- confirmation flag
    # authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "TENANT"))
):
    # if not is_deleted:
    #     return HttpStatusCode.OK.response(
    #         message="Delete confirmation required",
    #         data={
    #             "tenant_id": str(tenant_id),
    #             "is_deleted": False,
    #             "info": "Pass ?is_deleted=true to delete this tenant"
    #         }
    #     )

    # token = authorization.split(" ")[1]
    # decoded = decode_access_token(token)
    # requester_id = UUID(decoded["sub"])

    return await delete_tenant(tenant_id, user_id, is_deleted)



