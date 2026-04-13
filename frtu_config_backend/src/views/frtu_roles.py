from datetime import UTC, datetime, timezone
from math import ceil
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
from src.schemas.frtu_roles import FRTURoleAdd, FRTURoleCreate, FRTURoleRead, FRTURoleReadEntity, FRTURoleReadPayload, FRTURoleUpdate
from src.services.permissions import _get_permissions_grouped, _user_can_view_all_roles
from src.services.role import _user_has_role
from src.services.user_access import is_child_of
from src.utils.jwt_tokens import decode_access_token

# async def create_role(data: FRTURoleCreate, creator_id: UUID | None = None):
#     existing = await FRTURoles.select(name=data.name)
#     if existing:
#         return HttpStatusCode.BAD_REQUEST.response("Role with this name already exists")

#     now = datetime.now(UTC).replace(tzinfo=None)

#     role = await FRTURoles.insert(
#         user_id=creator_id,
#         name=data.name,
#         description=None,
#         attribute={},
#         creation_time=now,
#         last_update_time=now,
#     )
#     perm_attribute = {
#         "resources": [
#             {
#                 "resource": item.resource,
#                 "action": item.action,   # list of actions
#             }
#             for item in data.permissions
#             if item.resource and item.action
#         ]
#     }

#     permission = await FRTUPermissions.insert(
#         user_id=creator_id,
#         attribute=perm_attribute,
#         creation_time=now,
#         last_update_time=now,
#     )

#     await FRTURolePermissions.insert(
#         role_id=role.id,
#         permission_id=permission.id,
#         creation_time=now,
#         last_update_time=now,
#     )

#     return {
#         "http_code": 201,
#         "code": "CREATED",
#         "message": "Role created successfully",
#         "data": {
#             "id": str(role.id),
#             "name": role.name,
#             "permissions": perm_attribute["resources"],
#         },
#     }

async def create_role(data: FRTURoleCreate, creator_id: UUID | None = None):
    input_name = data.name.strip()
    normalized_input = input_name.lower()

    existing_roles = await FRTURoles.select()

    for r in existing_roles:
        if r.name and r.name.strip().lower() == normalized_input:
            return HttpStatusCode.BAD_REQUEST.response(
                f"Role '{input_name}' already exists"
            )

    now = datetime.now(UTC).replace(tzinfo=None)

    role = await FRTURoles.insert(
        user_id=creator_id,
        name=input_name,
        description=None,
        attribute={},
        creation_time=now,
        last_update_time=now
    )

    perm_attribute = {
        "resources": [
            {"resource": item.resource, "action": item.action}
            for item in data.permissions
            if item.resource and item.action
        ]
    }

    permission = await FRTUPermissions.insert(
        user_id=creator_id,
        attribute=perm_attribute,
        creation_time=now,
        last_update_time=now
    )

    await FRTURolePermissions.insert(
        role_id=role.id,
        permission_id=permission.id,
        creation_time=now,
        last_update_time=now
    )

    return {
        "http_code": 201,
        "code": "CREATED",
        "message": "Role created successfully",
        "data": {
            "id": str(role.id),
            "name": role.name,
            "permissions": perm_attribute["resources"]
        }
    }

# -------- list/search for current user --------
async def read_roles(page: int, limit: int, name: str | None, user_id: UUID):
    created_roles = await FRTURoles.select(user_id=user_id)

    assignments = await FRTUUserAssignment.select(user_id=user_id)
    assigned_role_ids = {a.role_id for a in assignments}

    assigned_roles = []
    if assigned_role_ids:
        assigned_roles = await FRTURoles.select(id=list(assigned_role_ids))

    role_map = {}
    for r in created_roles:
        role_map[r.id] = r
    # for r in assigned_roles:
    #     role_map[r.id] = r

    roles = list(role_map.values())

    if name:
        s = name.lower()
        roles = [r for r in roles if r.name and s in r.name.lower()]

    total = len(roles)
    start = (page - 1) * limit
    end = start + limit
    page_roles = roles[start:end]

    grouped = await _get_permissions_grouped([r.id for r in page_roles])

    roles_data = []
    for r in page_roles:
        grouped_perms = grouped.get(r.id, {})
        perms_out = [
            {"resource": res, "actions": sorted(list(actions))}
            for res, actions in grouped_perms.items()
        ]

        roles_data.append(
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "permissions": perms_out,
            }
        )

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Roles fetched successfully",
        "page": page,
        "page_size": limit,
        "total_records": total,
        "total_pages": ceil(total / limit) if limit else 1,
        "roles": roles_data,
    }

# -------- get single role by id for current user --------
# async def read_role_by_id(role_id: UUID, user_id: UUID):
#     can_view_all = await _user_can_view_all_roles(user_id)

#     if not can_view_all:
#         assigned = await FRTUUserAssignment.select(user_id=user_id, role_id=role_id)
#         if not assigned:
#             return HttpStatusCode.ACCESS_DENIED.response(
#                 "You are not allowed to view this role"
#             )

#     roles = await FRTURoles.select(id=role_id)
#     if not roles:
#         return HttpStatusCode.NOT_FOUND.response("Role not found")
#     role = roles[0]

#     grouped = await _get_permissions_grouped([role.id])
#     grouped_perms = grouped.get(role.id, {})

#     perms_out = [
#         {"resource": res, "actions": sorted(list(actions))}
#         for res, actions in grouped_perms.items()
#     ]

#     return {
#         "http_code": 200,
#         "code": "OK",
#         "message": "Role fetched successfully",
#         "id": str(role.id),
#         "name": role.name,
#         "description": role.description,
#         "permissions": perms_out,
#     }

async def read_role_by_id(role_id: UUID, user_id: UUID):
    roles = await FRTURoles.select(id=role_id)
    if not roles:
        return HttpStatusCode.NOT_FOUND.response("Role not found")

    role = roles[0]

    can_view_all = await _user_can_view_all_roles(user_id)

    # if not can_view_all:
    #     if role.user_id != user_id:
    #         assigned = await FRTUUserAssignment.select(
    #             user_id=user_id,
    #             role_id=role_id,
    #         )
    #         if not assigned:
    #             return HttpStatusCode.ACCESS_DENIED.response(
    #                 "You are not allowed to view this role"
    #             )
    if not can_view_all:
        allowed = False

        if role.user_id == user_id:
            allowed = True
        elif await is_child_of(user_id, role.user_id):
            allowed = True
        else:
            assigned = await FRTUUserAssignment.select(
                user_id=user_id,
                role_id=role_id,
            )
            if assigned:
                allowed = True

        if not allowed:
            return HttpStatusCode.ACCESS_DENIED.response(
                "You are not allowed to view this role"
            )
    grouped = await _get_permissions_grouped([role.id])
    grouped_perms = grouped.get(role.id, {})

    perms_out = [
        {"resource": res, "actions": sorted(list(actions))}
        for res, actions in grouped_perms.items()
    ]

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Role fetched successfully",
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "permissions": perms_out,
    }


async def update_role(role_id: UUID, data: FRTURoleUpdate, updater_id: UUID | None = None):
    if updater_id is not None:
        if await _user_has_role(updater_id, role_id):
            return HttpStatusCode.ACCESS_DENIED.response(
                "You are not allowed to update a role assigned to yourself"
            )
    roles = await FRTURoles.select(id=role_id)
    if not roles:
        return HttpStatusCode.NOT_FOUND.response("Role not found")
    role_obj = roles[0]

    role_snapshot = {
        "id": role_obj.id,
        "name": role_obj.name,
        "description": role_obj.description,
    }

    now = datetime.now(UTC).replace(tzinfo=None)

    role_updates = {}

    if data.name is not None:
        new_name = data.name.strip()
        if new_name != role_snapshot["name"]:
            existing = await FRTURoles.select(name=new_name)
            if existing and existing[0].id != role_id:
                return HttpStatusCode.BAD_REQUEST.response("Role with this name already exists")
            role_updates["name"] = new_name

    if data.description is not None:
        role_updates["description"] = data.description

    if role_updates:
        role_updates["last_update_time"] = now
        await FRTURoles.update(conditions={"id": role_id}, **role_updates)

    perm_attribute = None

    if data.permissions is not None:
        rps = await FRTURolePermissions.select(role_id=role_id)
        if not rps:
            return HttpStatusCode.BAD_REQUEST.response(
                "No permission mapping found for this role"
            )
        permission_id = rps[0].permission_id

        perms = await FRTUPermissions.select(id=permission_id)
        if not perms:
            return HttpStatusCode.BAD_REQUEST.response(
                "Permission record not found for this role"
            )
        perm_obj = perms[0]
        existing_attr = perm_obj.attribute or {}
        existing_resources = existing_attr.get("resources") or []
        existing_by_res = {item.get("resource"): item for item in existing_resources if item.get("resource")}

        for item in data.permissions:
            if not item.resource or not item.action:
                continue
            if item.resource in existing_by_res:
                existing_by_res[item.resource]["action"] = item.action
            else:
                existing_by_res[item.resource] = {
                    "resource": item.resource,
                    "action": item.action,
                }

        merged_resources = list(existing_by_res.values())
        perm_attribute = {"resources": merged_resources}

        await FRTUPermissions.update(
            conditions={"id": permission_id},
            attribute=perm_attribute,
            last_update_time=now,
        )

    final_name = data.name if data.name is not None else role_snapshot["name"]
    final_desc = (
        data.description if data.description is not None else role_snapshot["description"]
    )

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Role updated successfully",
        "data": {
            "id": str(role_id),
            "name": final_name,
            "description": final_desc,
            "permissions": perm_attribute["resources"] if perm_attribute else None,
        },
    }

async def delete_role(role_id: UUID, updater_id: UUID | None = None, is_deleted: bool = False):
    roles = await FRTURoles.select(id=role_id)
    if not roles:
        return HttpStatusCode.NOT_FOUND.response("Role not found")
    role = roles[0]

    if updater_id is not None and await _user_has_role(updater_id, role_id):
        return HttpStatusCode.ACCESS_DENIED.response(
            "You are not allowed to delete a role assigned to yourself"
        )
    assignments = await FRTUUserAssignment.select(role_id=role_id)
    has_assignments = bool(assignments)
    if not is_deleted:
        assigned_users: list[str] = []
        if has_assignments:
            user_ids = [a.user_id for a in assignments]
            users = await FRTUUsers.select(id=user_ids)
            assigned_users = [u.name for u in users]

        return {
            "http_code": 200,
            "code": "ROLE_STATUS",
            "message": (
                "Role is assigned to users; cannot be deleted."
                if has_assignments
                else "Role is not assigned to any user and can be deleted."
            ),
            "is_deleted": False if has_assignments else True,
            "data": {
                "role_id": str(role_id),
                "role_name": role.name,
                "assigned_users": assigned_users,
            },
        }
    if has_assignments:
        user_ids = [a.user_id for a in assignments]
        users = await FRTUUsers.select(id=user_ids)
        assigned_users = [u.name for u in users]
        return {
            "http_code": 400,
            "code": "ROLE_IN_USE",
            "message": "You cannot delete this role because it is mapped to one or more users.",
            "is_deleted": False,
            "data": {
                "role_id": str(role_id),
                "role_name": role.name,
                "assigned_users": assigned_users,
            },
        }

    rps = await FRTURolePermissions.select(role_id=role_id)
    perm_ids = [rp.permission_id for rp in rps]

    if rps:
        await FRTURolePermissions.delete(conditions={"role_id": role_id})

    if perm_ids:
        await FRTUPermissions.delete(conditions={"id": perm_ids[0]})

    await FRTURoles.delete(conditions={"id": role_id})

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Role deleted successfully",
        "is_deleted": True,
    }