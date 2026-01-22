from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers


async def create_role(payload, creator_id: UUID):
    return await FRTURoles.insert(
        user_id=creator_id,
        name=payload.name,
        description=payload.description,
        attribute=payload.attribute or {},
        creation_time=datetime.now(UTC),
        last_update_time=datetime.now(UTC),
    )

async def list_roles(current_user_id: UUID):
    users = await FRTUUsers.select(attribute__contains={"created_by": str(current_user_id)})
    child_ids = [u.id for u in users]

    return await FRTURoles.select(user_id__in=[current_user_id, *child_ids])

async def create_permission(payload, creator_id: UUID):
    return await FRTUPermissions.insert(
        user_id=creator_id,
        attribute=payload.attribute,
        creation_time=datetime.now(UTC),
        last_update_time=datetime.now(UTC),
    )

async def assign_permission_to_role(payload, current_user_id: UUID):
    role = (await FRTURoles.select(id=payload.role_id))[0]
    if role.user_id != current_user_id:
        raise HTTPException(403, "You cannot modify this role")

    return await FRTURolePermissions.insert(
        role_id=payload.role_id,
        permission_id=payload.permission_id,
        creation_time=datetime.now(UTC),
    )

async def assign_role_to_user(payload, admin_id: UUID):
    user = (await FRTUUsers.select(id=payload.user_id))[0]

    if user.attribute.get("created_by") != str(admin_id):
        raise HTTPException(403, "You can assign roles only to your own users")

    return await FRTUUserAssignment.insert(
        user_id=payload.user_id,
        role_id=payload.role_id,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        admin_id=admin_id,
        attribute={},
        creation_time=datetime.now(UTC),
        last_update_time=datetime.now(UTC),
    )

async def check_permission(
    user_id: UUID,
    resource: str,
    action: str,
    scope_type: str,
    scope_id: UUID | None
):
    assignments = await FRTUUserAssignment.select(
        user_id=user_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )

    for a in assignments:
        rps = await FRTURolePermissions.select(role_id=a.role_id)
        for rp in rps:
            perm = (await FRTUPermissions.select(id=rp.permission_id))[0]
            for rule in perm.attribute:
                if rule["resource"] == resource and action in rule["action"]:
                    return True

    raise HTTPException(403, "Permission denied")

async def get_my_rbac_info(user_id: UUID):
    user = (await FRTUUsers.select(id=user_id))[0]

    assignments = await FRTUUserAssignment.select(user_id=user_id)

    roles = []
    permissions = []

    for a in assignments:
        role = (await FRTURoles.select(id=a.role_id))[0]
        roles.append({
            "role_id": str(role.id),
            "role_name": role.name
        })

        role_perms = await FRTURolePermissions.select(role_id=role.id)
        for rp in role_perms:
            perm = (await FRTUPermissions.select(id=rp.permission_id))[0]
            permissions.extend(perm.attribute)

    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email
        },
        "roles": roles,
        "permissions": permissions
    }

async def get_users_created_by_me(user_id: UUID):
    users = await FRTUUsers.select()
    result = []

    for u in users:
        created_by = (u.attribute or {}).get("created_by")
        if created_by == str(user_id):
            result.append({
                "id": str(u.id),
                "name": u.name,
                "email": u.email,
                "mobile_no": u.mobile_no
            })

    return {
        "count": len(result),
        "users": result
    }

async def get_roles_visible_to_me(user_id: UUID):
    roles = await FRTURoles.select()
    visible = []

    for r in roles:
        if r.user_id == user_id:
            visible.append(r)
        else:
            owner = (await FRTUUsers.select(id=r.user_id))[0]
            if owner.attribute.get("created_by") == str(user_id):
                visible.append(r)

    return [
        {
            "role_id": str(r.id),
            "name": r.name,
            "description": r.description
        }
        for r in visible
    ]
