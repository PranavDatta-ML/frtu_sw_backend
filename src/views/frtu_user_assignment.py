# src/views/user_assignment.py
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException
from src.models.frtu_entities import FRTUEntities
from src.models.frtu_platform_admins import FRTUPlatformAdmin
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_roles import FRTURoles
from src.models.frtu_users import FRTUUsers
from src.core.status_codes import HttpStatusCode
from src import log

import uuid

# async def assign_role_to_user(payload: dict, assigned_by: UUID):
#     user_id = payload.get("user_id")
#     role_id = payload.get("role_id")
#     scope_type = payload.get("scope_type")
#     scope_id = payload.get("scope_id")
#     attribute = payload.get("attribute") or {}

#     if not scope_id:
#         scope_id = uuid.uuid4()

#     assignment = await FRTUUserAssignment.insert(
#         user_id=user_id,
#         role_id=role_id,
#         scope_type=scope_type,
#         scope_id=scope_id,
#         attribute=attribute,
#         creation_time=datetime.utcnow(),
#         last_update_time=datetime.utcnow()
#     )

#     return {
#         "id": str(assignment.id),
#         "user_id": str(assignment.user_id),
#         "role_id": str(assignment.role_id),
#         "scope_type": assignment.scope_type,
#         "scope_id": str(assignment.scope_id),
#         "attribute": assignment.attribute or {},
#         "assigned_by": str(assigned_by)
#     }


async def assign_role_to_user(payload: dict, assigned_by: UUID):

    user_id = payload.get("user_id")
    role_id = payload.get("role_id")
    scope_type = payload.get("scope_type")
    scope_id = payload.get("scope_id")
    admin_id = payload.get("admin_id")
    attribute = payload.get("attribute") or {}

    if not scope_id:
        scope_id = uuid.uuid4()

    assigner = await FRTUUsers.select(id=assigned_by)
    if not assigner:
        return HttpStatusCode.BAD_REQUEST.response("Assigner user not found")
    assigner = assigner[0]

    assignments = await FRTUUserAssignment.select(user_id=assigned_by)
    if not assignments:
        return HttpStatusCode.BAD_REQUEST.response("Assigner role not found")
    assigner_role_id = assignments[0].role_id

    roles = await FRTURoles.select(id=assigner_role_id)
    if not roles:
        return HttpStatusCode.BAD_REQUEST.response("Invalid assigner role")
    role_name = roles[0].name.lower().strip()

    if role_name == "platform admin":
        pa = await FRTUPlatformAdmin.select(email=assigner.email)
        if not pa:
            return HttpStatusCode.BAD_REQUEST.response("Platform Admin profile missing for assigner")

    elif role_name in ["admin", "super admin"]:
        entities = await FRTUEntities.select(created_by=assigned_by)
        if not entities:
            return HttpStatusCode.BAD_REQUEST.response("No Platform Admin mapped to this Admin")

    else:
        return HttpStatusCode.FORBIDDEN.response("You are not allowed to assign roles")

    existing = await FRTUUserAssignment.select(
        user_id=user_id,
        role_id=role_id,
        admin_id=admin_id
    )

    if existing:
        return HttpStatusCode.BAD_REQUEST.response(
            "This user already has this role under the same admin"
        )

    assignment = await FRTUUserAssignment.insert(
        user_id=user_id,
        role_id=role_id,
        scope_type=scope_type,
        scope_id=scope_id,
        admin_id=admin_id,
        attribute=attribute,
        creation_time=datetime.utcnow(),
        last_update_time=datetime.utcnow()
    )

    return {
        "id": str(assignment.id),
        "user_id": str(assignment.user_id),
        "role_id": str(assignment.role_id),
        "scope_type": assignment.scope_type,
        "scope_id": str(assignment.scope_id),
        "admin_id": str(admin_id),
        "attribute": assignment.attribute or {},
        "assigned_by": str(assigned_by)
    }

async def list_user_assignments(user_id: UUID):
    records = await FRTUUserAssignment.select(user_id=user_id)
    return records


async def get_user_assignment(assignment_id: UUID):
    rec = await FRTUUserAssignment.select(id=assignment_id)
    if not rec:
        raise HTTPException(404, "User assignment not found")
    return rec[0]


async def update_user_assignment(assignment_id: UUID, update_data, updated_by: UUID):
    rec = await FRTUUserAssignment.select(id=assignment_id)
    if not rec:
        raise HTTPException(404, "Assignment not found")
    obj = rec[0]

    if update_data.role_id is not None:
        obj.role_id = update_data.role_id

    if update_data.scope_type is not None:
        obj.scope_type = update_data.scope_type

    if update_data.scope_id is not None:
        obj.scope_id = update_data.scope_id

    if update_data.attribute is not None:
        obj.attribute = update_data.attribute

    obj.last_update_time = datetime.utcnow()
    await obj.update()

    return {
        "id": obj.id,
        "user_id": obj.user_id,
        "role_id": obj.role_id,
        "scope_type": obj.scope_type,
        "scope_id": obj.scope_id,
        "attribute": obj.attribute or {},
        "assigned_by": updated_by,
        "creation_time": obj.creation_time,
        "last_update_time": obj.last_update_time
    }


async def delete_user_assignment(assignment_id: UUID):
    rec = await FRTUUserAssignment.select(id=assignment_id)
    if not rec:
        raise HTTPException(404, "Assignment not found")

    await rec[0].delete()
    return {"message": "User assignment deleted successfully"}

