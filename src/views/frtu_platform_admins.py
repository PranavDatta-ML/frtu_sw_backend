from datetime import datetime
from uuid import UUID
from fastapi import HTTPException, status

from src.models.frtu_entities import FRTUEntities
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_users import FRTUUsers
from src.schemas.frtu_platform_admins import FRTUPlatformAdminCreate
from src.schemas.frtu_users import FRTUUserCreate
from src.utils.security import generate_salt, hash_password


async def create_platform_admin(data: FRTUPlatformAdminCreate, creator_id: UUID):

    existing = await FRTUPlatformAdmin.select(email=data.email)
    if existing:
        raise HTTPException(400, "Platform admin with this email already exists")

    existing = await FRTUPlatformAdmin.select(mobile_no=data.mobile_no)
    if existing:
        raise HTTPException(400, "Platform admin with this mobile number already exists")

    # INSERT USING CLASSMETHOD
    platform_admin = await FRTUPlatformAdmin.insert(
        name=data.name,
        email=data.email,
        mobile_no=data.mobile_no,
        attribute=data.attribute,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )

    # add entity
    # await FRTUEntities.insert(
    #     entity_id=platform_admin.id,
    #     # entity_type="PLATFORM_ADMIN",
    #     created_by=creator_id,
    #     creation_time=datetime.utcnow(),
    #     last_update_time=datetime.utcnow()
    # )

    await FRTUEntities.insert(
        entity_id=platform_admin.id,
        name=platform_admin.name,
        email_id=platform_admin.email,
        mobile_no=platform_admin.mobile_no,
        created_by=creator_id,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )
    
    # return platform_admin
    response = {
        **platform_admin.__dict__,
        "created_by": creator_id,
    }

    return response



async def create_user(data: FRTUUserCreate, creator_id: UUID):

    if not isinstance(creator_id, UUID):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid creator_id"
        )

    if await FRTUUsers.select(email=data.email):
        raise HTTPException(status_code=400, detail="User with this email already exists")

    if await FRTUUsers.select(mobile_no=data.mobile_no):
        raise HTTPException(status_code=400, detail="User with this mobile number already exists")

    salt = generate_salt()
    password_hash = hash_password(data.password, salt)

    user = FRTUUsers(
        email=data.email,
        mobile_no=data.mobile_no,
        name=data.name,
        password_hash=password_hash,
        salt=salt,
        is_active=True,
        is_deleted=False,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow(),
    )
    user = await user.insert()
    entity = FRTUEntities(
        entity_id=user.id,
        entity_type="USER",
        created_by=creator_id,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )
    await entity.insert()

    return user



