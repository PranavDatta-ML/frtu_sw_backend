from fastapi import APIRouter, Depends, Body
from uuid import UUID

from src.middleware.CreatePermissionMiddleware import require_create_permission
from src.schemas.frtu_users import FRTUUserCreate, FRTUUserRead
from src.views.frtu_users import create_user

router = APIRouter(
    prefix="/api/users",
    tags=["frtu_users"]
)

@router.post("/", response_model=FRTUUserRead)
async def api_create_user(
    data: FRTUUserCreate,
    user_id: UUID = Depends(require_create_permission)
):
    print("DEBUG => payload received:", data.dict())
    return await create_user(data, creator_id=user_id)

     

