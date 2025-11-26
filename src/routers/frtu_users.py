from fastapi import APIRouter, Depends, Body
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission, require_permission
from src.schemas.frtu_users import FRTUUserCreate, FRTUUserRead, FRTUUserUpdate
from src.views.frtu_users import create_user, delete_user, get_user, update_user

router = APIRouter(
    prefix="/api/users",
    tags=["frtu_users"]
)

@router.post("/", response_model=FRTUUserRead)
async def api_create_user(data: FRTUUserCreate,user_id: UUID = Depends(require_permission("edit", "USER"))):
    print("DEBUG => payload received:", data.dict())
    return await create_user(data, creator_id=user_id)


@router.get("/{user_id}", response_model=FRTUUserRead)
async def api_get_user(user_id: UUID, _ = Depends(require_permission("view", "USER"))):    
    return await get_user(user_id)  


@router.put("/{user_id}", response_model=FRTUUserRead)
async def api_update_user(user_id: UUID,update_data: FRTUUserUpdate,current_user: UUID = Depends(require_permission("edit", "USER"))):
    return await update_user(user_id, update_data)


@router.delete("/{user_id}")
async def api_delete_user(user_id: UUID,current_user: UUID = Depends(require_permission("edit", "USER"))):
    return await delete_user(user_id)