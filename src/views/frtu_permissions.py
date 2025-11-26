

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from src.models.frtu_permissions import FRTUPermissions
from src.schemas.frtu_permissions import FRTUPermissionCreate, FRTUPermissionRead, FRTUPermissionUpdate


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
    # permissions = await FRTUPermissions.select().offset(skip).limit(limit)
    # return [FRTUPermissionRead.from_orm(p) for p in permissions]
    permissions = await FRTUPermissions.select()
    return permissions[skip: skip + limit]


async def get_permission(permission_id: UUID) -> FRTUPermissionRead:
    # try:
    #     creator_permission_uuid = UUID(permission_id)
    # except Exception:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid creator_id")
    permission = await FRTUPermissions.select(id = permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    # return FRTUPermissionRead.from_orm(permission)
    return permission[0]

# async def update_permission(permission_id: UUID, permission_update: FRTUPermissionUpdate) -> FRTUPermissionRead:
#     permission = await FRTUPermissions.select(id = permission_id)
#     if not permission:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

#     if permission_update.attribute is not None:
#         permission.attribute = permission_update.attribute
#     permission.last_update_time = datetime.utcnow()
#     await permission.update()
#     return FRTUPermissionRead.from_orm(permission)

async def update_permission(permission_id: UUID, permission_update: FRTUPermissionUpdate) -> FRTUPermissionRead:
    records = await FRTUPermissions.select(id=permission_id)

    if not records:
        now = datetime.utcnow()

        payload = permission_update.attribute or {}
        resources = payload.get("resources", [])

        if "resource" in payload and "action" in payload:
            resources.append({
                "resource": payload["resource"],
                "action": payload["action"]
            })

        new_attr = {"resources": resources}

        new_perm = await FRTUPermissions.insert(
            id=permission_id,
            attribute=new_attr,
            creation_time=now,
            last_update_time=now
        )
        return FRTUPermissionRead.from_orm(new_perm)

    permission = records[0]
    old_attr = permission.attribute or {}

    old_resources = old_attr.get("resources", [])

    payload = permission_update.attribute or {}
    new_resources = payload.get("resources", [])

    if "resource" in payload and "action" in payload:
        new_resources.append({
            "resource": payload["resource"],
            "action": payload["action"]
        })

    final_resources = old_resources.copy()

    for nr in new_resources:
        exists = any(r["resource"] == nr["resource"] for r in final_resources)
        if not exists:
            final_resources.append(nr)
        else:
            for r in final_resources:
                if r["resource"] == nr["resource"]:
                    r["action"] = list(set(r["action"] + nr["action"]))

    final_attribute = {"resources": final_resources}

    now = datetime.utcnow()

    await FRTUPermissions.update(
        conditions={"id": permission_id},
        attribute=final_attribute,
        last_update_time=now
    )

    updated = await FRTUPermissions.select(id=permission_id)
    return FRTUPermissionRead.from_orm(updated[0])


async def delete_permission(permission_id: UUID):
    permission = await FRTUPermissions.select(id = permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    # await permission.delete()
    await FRTUPermissions.delete(id = permission_id)
    return {"message": "Permission deleted successfully"}




