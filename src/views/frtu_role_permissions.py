
from fastapi import HTTPException, Request, Header, Depends, status
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_users import FRTUUsers
from src.core.status_codes import HttpStatusCode
from src.schemas.frtu_role_permissions import AssignRolePermission, FRTURolePermissionBase
from src.utils.jwt_tokens import decode_access_token
from src.core.settings import Settings
from src import log
from datetime import UTC, datetime
import uuid
from uuid import UUID


async def assign_permission_to_role(data: AssignRolePermission, assigned_by: UUID):

    role = await FRTURoles.select(id=data.role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    role = role[0]

    role_created_by = role.user_id
    # if isinstance(role.attribute, dict):
    #     role_created_by = role.attribute.get("created_by")

    perm = await FRTUPermissions.select(id=data.permission_id)
    if not perm:
        raise HTTPException(404, "Permission not found")
    perm = perm[0]

    permission_created_by = perm.user_id

    existing = await FRTURolePermissions.select(
        role_id=data.role_id,
        permission_id=data.permission_id
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="This permission is already assigned to this role"
        )

    mapping = await FRTURolePermissions.insert(
        role_id=data.role_id,
        permission_id=data.permission_id,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow(),
    )

    return {
        "role_id": mapping.role_id,
        "permission_id": mapping.permission_id,

        "assigned_by": assigned_by,
        "role_created_by": role_created_by,
        "permission_created_by": permission_created_by,

        "creation_time": mapping.creation_time,
        "last_update_time": mapping.last_update_time,
    }


async def list_role_permissions(role_id: UUID):
    records = await FRTURolePermissions.select(role_id=role_id)
    return records


async def get_role_permission(role_id: UUID, permission_id: UUID):
    result = await FRTURolePermissions.select(role_id=role_id, permission_id=permission_id)
    if not result:
        raise HTTPException(404, "Role-permission mapping not found")
    return result[0]


async def update_role_permission(role_id: UUID,permission_id: UUID,new_permission_id: UUID,updated_by: UUID,):
    existing = await FRTURolePermissions.select(role_id=role_id, permission_id=permission_id)
    if not existing:
        raise HTTPException(404, "Mapping not found")

    new_perm = await FRTUPermissions.select(id=new_permission_id)
    if not new_perm:
        raise HTTPException(404, "New permission does not exist")

    dup = await FRTURolePermissions.select(role_id=role_id, permission_id=new_permission_id)
    if dup:
        raise HTTPException(400, "This permission already assigned to this role")

    mapping = existing[0]
    mapping.permission_id = new_permission_id
    mapping.last_update_time = datetime.utcnow()
    await mapping.update()

    return {
        "role_id": mapping.role_id,
        "permission_id": mapping.permission_id,
        "assigned_by": updated_by,
        "creation_time": mapping.creation_time,
        "last_update_time": mapping.last_update_time
    }


async def delete_role_permission(role_id: UUID, permission_id: UUID):
    record = await FRTURolePermissions.select(role_id=role_id, permission_id=permission_id)
    if not record:
        raise HTTPException(404, "Role-permission mapping not found")

    await record[0].delete()

    return {"message": "Permission removed from role"}

# async def remove_permission_from_role(role_id: UUID,permission_id: UUID,removed_by: UUID):
#     existing = await FRTURolePermissions.select(
#         role_id=role_id,
#         permission_id=permission_id
#     )

#     if not existing:
#         raise HTTPException(
#             status_code=404,
#             detail="This permission is not assigned to this role"
#         )

#     await FRTURolePermissions.delete(
#         conditions={
#             "role_id": role_id,
#             "permission_id": permission_id
#         }
#     )

#     return {
#         "role_id": role_id,
#         "permission_id": permission_id,
#         "removed_by": removed_by,
#         "removal_time": datetime.utcnow(),
#     }


