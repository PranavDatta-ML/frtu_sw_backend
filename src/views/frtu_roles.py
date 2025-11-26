from datetime import UTC, datetime, timezone
from typing import List
from src import log
from uuid import UUID
import uuid
from fastapi import Depends, HTTPException, Header, Request, status
from src.core.settings import Settings
from src.core.status_codes import HttpStatusCode
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models import FRTUUsers, FRTURoles, FRTUUserAssignment, FRTUPermissions, FRTURolePermissions, FRTUResources
from src.schemas.frtu_roles import FRTURoleCreate, FRTURoleRead, FRTURoleUpdate
from src.utils.jwt_tokens import decode_access_token


async def create_role(role_create: FRTURoleCreate, user_id: str) -> FRTURoleRead:
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user_id in request")

    try:
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format")
    
    existing_roles = await FRTURoles.select(name=role_create.name)
    if existing_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role already exists")

    role = await FRTURoles.insert(
        user_id=user_uuid,
        name=role_create.name,
        description=role_create.description,
        attribute=role_create.attribute,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )
    # await role.insert()
    return FRTURoleRead.from_orm(role)

async def list_roles(skip: int = 0, limit: int = 100) -> List[FRTURoleRead]:
    # roles = await FRTURoles.select(offset=skip, limit=limit)
    # return [FRTURoleRead.from_orm(FRTURoles(**role)) for role in roles]
    roles = await FRTURoles.select()
    return roles[skip: skip + limit]


async def get_role(role_id: UUID) -> FRTURoleRead:
    # try:
    #     role_uuid = UUID(role_id)
    # except Exception:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id")
    role = await FRTURoles.select(id = role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    # return FRTURoleRead.from_orm(role)
    return role[0]


async def update_role(role_id: UUID, role_update: FRTURoleUpdate) -> FRTURoleRead:
    role = await FRTURoles.select(id = role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role_update.name:
        role.name = role_update.name
    if role_update.description:
        role.description = role_update.description
    role.last_update_time = datetime.utcnow()
    await role.update()

    if role_update.permission_ids is not None:
        await FRTURolePermissions.delete_many(role_id=role_id)
        for permission_id in role_update.permission_ids:
            rp = FRTURolePermissions(role_id=role_id, permission_id=permission_id)
            await rp.insert()

    return FRTURoleRead.from_orm(role)

async def delete_role(role_id: UUID):
    role = await FRTURoles.select(id = role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    # await role.delete()
    await FRTURoles.delete(id = role_id)
    return {"message": "Role deleted successfully"}


