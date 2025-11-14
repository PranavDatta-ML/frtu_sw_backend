

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from src.models.frtu_permissions import FRTUPermissions
from src.schemas.frtu_permissions import FRTUPermissionCreate, FRTUPermissionRead, FRTUPermissionUpdate


# async def create_permission(permission_create: FRTUPermissionCreate, user_id: UUID) -> FRTUPermissionRead:
#     # try:
#     #     creator_uuid = UUID(user_id)
#     # except Exception:
#     #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid creator_id")
#     permission = await FRTUPermissions.insert(
#         user_id=user_id,
#         attribute=permission_create.attribute,
#         creation_time=datetime.utcnow(),
#         last_update_time=datetime.utcnow()
#     )
#     # await permission.insert()
#     return FRTUPermissionRead.from_orm(permission)

async def create_permission(permission_create: FRTUPermissionCreate, user_id: UUID) -> FRTUPermissionRead:
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing creator user_id")

    if not isinstance(permission_create.attribute, list) or len(permission_create.attribute) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 'attribute' format. Expected list of resources/actions.")

    formatted_attribute = {
        "resources": [
            {
                "resource": item.get("resource"),
                # "resource_id": item.get("resource_id", ""),  
                "action": item.get("action", [])
            }
            for item in permission_create.attribute
        ]
    }

    permission = await FRTUPermissions.insert(
        user_id=user_id,
        attribute=formatted_attribute,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )

    return FRTUPermissionRead.from_orm(permission)



async def list_permissions(skip: int = 0, limit: int = 100) -> List[FRTUPermissionRead]:
    permissions = await FRTUPermissions.select().offset(skip).limit(limit)
    return [FRTUPermissionRead.from_orm(p) for p in permissions]

async def get_permission(permission_id: str) -> FRTUPermissionRead:
    try:
        creator_permission_uuid = UUID(permission_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid creator_id")
    permission = await FRTUPermissions.get(creator_permission_uuid)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return FRTUPermissionRead.from_orm(permission)

async def update_permission(permission_id: str, permission_update: FRTUPermissionUpdate) -> FRTUPermissionRead:
    try:
        creator_permission_uuid = UUID(permission_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid creator_id")
    permission = await FRTUPermissions.get(creator_permission_uuid)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    if permission_update.attribute is not None:
        permission.attribute = permission_update.attribute
    permission.last_update_time = datetime.utcnow()
    await permission.update()
    return FRTUPermissionRead.from_orm(permission)

async def delete_permission(permission_id: str):
    try:
        creator_permission_uuid = UUID(permission_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid creator_id")
    permission = await FRTUPermissions.get(creator_permission_uuid)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    await permission.delete()




