# src/views/user_assignment.py
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_roles import FRTURoles
from src.models.frtu_users import FRTUUsers
from src.core.status_codes import HttpStatusCode
from src import log

import uuid

async def assign_role_to_user(payload: dict, assigned_by: UUID):
    user_id = payload.get("user_id")
    role_id = payload.get("role_id")
    scope_type = payload.get("scope_type")
    scope_id = payload.get("scope_id")
    attribute = payload.get("attribute") or {}

    # Auto generate scope_id when NOT provided
    if not scope_id:
        scope_id = uuid.uuid4()

    # insert into DB
    assignment = await FRTUUserAssignment.insert(
        user_id=user_id,
        role_id=role_id,
        scope_type=scope_type,
        scope_id=scope_id,
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
        "attribute": assignment.attribute or {},
        "assigned_by": str(assigned_by)
    }


async def remove_user_assignment(user_id: UUID, role_id: UUID, scope_type: str = None, scope_id: UUID = None):
    """
    Remove an assignment. Matches on provided fields; if scope_type provided match it.
    """
    try:
        conditions = {"user_id": user_id, "role_id": role_id}
        if scope_type:
            conditions["scope_type"] = scope_type.upper()
        if scope_id:
            conditions["scope_id"] = scope_id

        existing = await FRTUUserAssignment.select(**conditions)
        if not existing:
            raise HTTPException(status_code=404, detail="Assignment not found")

        # delete all matching assignments (normally one)
        await FRTUUserAssignment.delete(conditions=conditions)
        return {"deleted": len(existing)}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"remove_user_assignment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove assignment")


async def list_user_assignments(user_id: UUID):
    try:
        rows = await FRTUUserAssignment.select(user_id=user_id)
        result = []
        for r in rows:
            result.append({
                "id": str(r.get("id") if isinstance(r, dict) else getattr(r, "id")),
                "user_id": str(r.get("user_id") if isinstance(r, dict) else getattr(r, "user_id")),
                "role_id": str(r.get("role_id") if isinstance(r, dict) else getattr(r, "role_id")),
                "scope_type": r.get("scope_type") if isinstance(r, dict) else getattr(r, "scope_type"),
                "scope_id": str(r.get("scope_id")) if isinstance(r, dict) and r.get("scope_id") else (str(getattr(r, "scope_id")) if getattr(r, "scope_id", None) else None),
                "attribute": r.get("attribute") if isinstance(r, dict) else getattr(r, "attribute", {}),
                "creation_time": r.get("creation_time").isoformat() if isinstance(r, dict) and r.get("creation_time") else (getattr(r, "creation_time").isoformat() if getattr(r, "creation_time", None) else None),
                "last_update_time": r.get("last_update_time").isoformat() if isinstance(r, dict) and r.get("last_update_time") else (getattr(r, "last_update_time").isoformat() if getattr(r, "last_update_time", None) else None),
            })
        return result
    except Exception as e:
        log.error(f"list_user_assignments error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list assignments")


