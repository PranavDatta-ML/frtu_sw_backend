from fastapi import APIRouter, Depends, Body, Header, Query
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission, require_permission
from src.schemas.frtu_users import FRTUUserAdd, FRTUUserCreate, FRTUUserRead, FRTUUserUpdate, FRTUUserUpdateById
from src.utils.jwt_tokens import decode_access_token
from src.views.frtu_users import add_user_api, create_user, delete_user, read_user_by_id, read_user_permissions, read_users, update_user_by_id

router = APIRouter(
    prefix="/api/users",
    tags=["frtu_users"]
)

@router.get("/permissions")
async def api_read_my_permissions(
    authorization: str = Header(...),
    caller_id: UUID = Depends(require_permission("view", "PERMISSION")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    user_id = UUID(decoded["sub"])
    return await read_user_permissions(user_id)

@router.post("/")
async def api_create_user(
    data: FRTUUserAdd,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "USER")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await create_user(data, creator_id=user_id)


@router.post("/users")
async def api_add_user(
    payload: FRTUUserAdd,
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("edit", "USER")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await add_user_api(payload, requester_id=requester_id)

@router.get("/")
async def api_read_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    search: str | None = Query(
        None, description="Search by name, email or mobile (partial)"
    ),
    authorization: str = Header(...),
    user_id: UUID = Depends(require_permission("view", "USER")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])  # available if you later want user-specific logic

    return await read_users(page=page, limit=limit, search=search)


@router.get("/{user_id}")
async def api_read_user_by_id(
    user_id: UUID,
    authorization: str = Header(...),
    caller_id: UUID = Depends(require_permission("view", "USER")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await read_user_by_id(user_id)


@router.put("/{user_id}")
async def api_update_user_by_id(
    user_id: UUID,
    payload: FRTUUserUpdateById,
    authorization: str = Header(...),
    caller_id: UUID = Depends(require_permission("edit", "USER")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    requester_id = UUID(decoded["sub"])
    return await update_user_by_id(user_id=user_id, data=payload, updater_id=requester_id)


@router.delete("/{user_id}")
async def api_delete_user(
    user_id: UUID,
    is_deleted: bool = Query(False, description="Must be true to actually delete"),
    authorization: str = Header(...),
    caller_id: UUID = Depends(require_permission("delete", "USER")),
):
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    deleter_id = UUID(decoded["sub"])
    return await delete_user(user_id=user_id, deleter_id=deleter_id, is_deleted=is_deleted)

