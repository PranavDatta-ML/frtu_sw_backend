from fastapi import APIRouter, Depends, Header, Path, Query
from typing import List
from uuid import UUID

from src.schemas.frtu_roles import FRTURoleAdd, FRTURoleCreate, FRTURoleReadPayload, FRTURoleUpdate, FRTURoleRead
from src.middleware.CreatePermissionMiddleware import require_permission
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_roles import create_role, delete_role, read_role_by_id, read_roles, update_role


# router = APIRouter(prefix="/roles", tags=["roles"])
router = APIRouter(prefix="/api", tags=["roles"])

@router.post("/roles", response_model=dict)
async def api_create_role(
    data: FRTURoleAdd,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "ROLES")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id =  UUID(decoded["sub"])
    return await create_role(data, creator_id=requester_id)


@router.get("/roles", response_model=dict)
async def api_read_roles(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    name: str | None = Query(None, description="Partial or exact role name"),
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "ROLES")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])      

    return await read_roles(
        page=page,
        limit=limit,
        name=name,
        user_id=requester_id,
    )


@router.get("/roles/{role_id}")
async def api_read_role_by_id(
    role_id: UUID,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "ROLES")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await read_role_by_id(role_id=role_id, user_id=requester_id)


@router.put("/roles/{role_id}")
async def api_update_role(
    role_id: UUID,
    payload: FRTURoleUpdate,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "ROLES")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])

    return await update_role(role_id=role_id, data=payload, updater_id=requester_id)

@router.delete("/roles/{role_id}")
async def api_delete_role(
    role_id: UUID,
    is_deleted: bool = Query(False, description="Must be true to actually delete"),
    authorization: str = Header(...),
    caller_id: UUID = Depends(require_permission("edit", "ROLES")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    updater_id = UUID(decoded["sub"])
    return await delete_role(role_id=role_id, updater_id=updater_id, is_deleted=is_deleted)


