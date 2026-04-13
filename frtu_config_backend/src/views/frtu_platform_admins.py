from datetime import datetime
from uuid import UUID
from fastapi import HTTPException, status

from src.models.frtu_entities import FRTUEntities
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
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


# async def get_platform_admin(platform_admin_id: UUID):
#     platform_admin = await FRTUPlatformAdmin.select(id=platform_admin_id)
#     if not platform_admin:
#         raise HTTPException(404, "Platform Admin not found")
#     return platform_admin[0]


async def get_platform_admin(platform_admin_id: UUID):
    rec = await FRTUPlatformAdmin.select(id=platform_admin_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform Admin not found"
        )

    platform_admin = rec[0]

    entity = await FRTUEntities.select(entity_id=platform_admin_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity mapping not found for platform admin"
        )
    entity = entity[0]

    return {
        "id": platform_admin.id,
        "name": platform_admin.name,
        "email": platform_admin.email,
        "mobile_no": platform_admin.mobile_no,
        "attribute": platform_admin.attribute,
        "created_by": entity.created_by,
        "creation_time": entity.creation_time,
        "last_update_time": entity.last_update_time,
    }


async def update_platform_admin(platform_admin_id: UUID, data):
    record = await FRTUPlatformAdmin.select(id=platform_admin_id)
    if not record:
        raise HTTPException(404, "Platform Admin not found")

    obj = record[0]

    if data.name is not None:
        obj.name = data.name

    if data.mobile_no is not None:
        obj.mobile_no = data.mobile_no

    if data.attribute is not None:
        obj.attribute = data.attribute

    obj.last_update_time = datetime.utcnow()
    await obj.update()

    entity = await FRTUEntities.select(entity_id=platform_admin_id)
    if entity:
        ent = entity[0]
        ent.name = obj.name
        ent.mobile_no = obj.mobile_no
        ent.last_update_time = datetime.utcnow()
        await ent.update()

    return {"message": "Platform Admin updated successfully"}


async def delete_platform_admin(platform_admin_id: UUID):
    rec = await FRTUPlatformAdmin.select(id=platform_admin_id)
    if not rec:
        raise HTTPException(404, "Platform Admin not found")

    entity = await FRTUEntities.select(entity_id=platform_admin_id)
    if entity:
        await entity[0].delete()

    await rec[0].delete()

    return {"message": "Platform Admin deleted successfully"}


async def list_platform_admins():
    admins = await FRTUPlatformAdmin.select()

    result = []
    for admin in admins:
        entity = await FRTUEntities.select(entity_id=admin.id)
        if entity:
            ent = entity[0]
            created_by = ent.created_by
            cts = ent.creation_time
            uts = ent.last_update_time
        else:
            created_by = None
            cts = None
            uts = None

        result.append({
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "mobile_no": admin.mobile_no,
            "attribute": admin.attribute,
            "created_by": created_by,
            "creation_time": cts,
            "last_update_time": uts
        })

    return result


# async def get_platform_admin_hierarchy(platform_admin_id: UUID):
#     rec = await FRTUPlatformAdmin.select(id=platform_admin_id)
#     if not rec:
#         raise HTTPException(404, "Platform Admin not found")

#     admin = rec[0]

#     assignments = await FRTUUserAssignment.select(user_id=platform_admin_id)

#     role_ids = [a.role_id for a in assignments]
#     roles = []
#     permissions = []

#     for rid in role_ids:
#         r = await FRTURoles.select(id=rid)
#         if r:
#             roles.append({
#                 "role_id": str(r[0].id),
#                 "role_name": r[0].name
#             })
#         role_perms = await FRTURolePermissions.select(role_id=rid)
#         for rp in role_perms:
#             pid = rp.permission_id
#             p = await FRTUPermissions.select(id=pid)
#             if p:
#                 permissions.append({
#                     "role_id": str(rid),
#                     "permission_id": str(pid),
#                     "permission": p[0].attribute
#                 })

#     return {
#         "platform_admin_id": admin.id,
#         "name": admin.name,
#         "email": admin.email,
#         "roles": roles,
#         "permissions": permissions
#     }


async def get_platform_admin_hierarchy(platform_admin_id: UUID):
    admin_rec = await FRTUPlatformAdmin.select(id=platform_admin_id)
    if not admin_rec:
        raise HTTPException(404, "Platform Admin not found")
    admin = admin_rec[0]

    entity_rec = await FRTUEntities.select(entity_id=platform_admin_id)
    if not entity_rec:
        return {
            "platform_admin_id": str(admin.id),
            "name": admin.name,
            "email": admin.email,
            "roles": [],
            "permissions": []
        }
    entity = entity_rec[0]
    actual_user_id = entity.created_by

    assignments = await FRTUUserAssignment.select(user_id=actual_user_id)

    roles = []
    permissions = []
    seen_roles = set()
    seen_perms = set()

    for a in assignments:
        role_id = a.role_id

        if role_id not in seen_roles:
            seen_roles.add(role_id)
            role_rec = await FRTURoles.select(id=role_id)
            if role_rec:
                r = role_rec[0]
                roles.append({
                    "role_id": str(r.id),
                    "role_name": r.name
                })

        role_perm_rec = await FRTURolePermissions.select(role_id=role_id)

        for rp in role_perm_rec:
            perm_id = rp.permission_id
            if perm_id in seen_perms:
                continue
            seen_perms.add(perm_id)

            perm_rec = await FRTUPermissions.select(id=perm_id)
            if perm_rec:
                p = perm_rec[0]
                permissions.append({
                    "role_id": str(role_id),
                    "permission_id": str(perm_id),
                    "permission": p.attribute
                })

    return {
        "platform_admin_id": str(admin.id),
        "name": admin.name,
        "email": admin.email,
        "roles": roles,
        "permissions": permissions
    }


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



