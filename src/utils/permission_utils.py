import logging
from typing import List
from uuid import UUID
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_permissions import FRTUPermissions
from sqlalchemy import or_

from src import log


async def user_has_permission(user_id, action: str, resource: str) -> bool:
    try:
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    except Exception:
        log.error(f"user_has_permission: Invalid user_id '{user_id}'")
        return False

    log.info(f"user_has_permission: Checking user_id={user_uuid}, action={action}, resource={resource}")

    user_assignments = await FRTUUserAssignment.select(user_id=user_uuid)
    if not user_assignments:
        log.info("user_has_permission: No user assignments found")
        return False

    role_ids = []
    for ua in user_assignments:
        if isinstance(ua, dict) and "FRTUUserAssignment" in ua:
            ua_obj = ua["FRTUUserAssignment"]
        elif hasattr(ua, "role_id"):
            ua_obj = ua
        elif hasattr(ua, "_mapping") and "role_id" in ua._mapping:
            ua_obj = ua._mapping
        else:
            log.warning(f"user_has_permission: Unknown row type: {ua}")
            continue

        rid = getattr(ua_obj, "role_id", None) or (
            ua_obj.get("role_id") if isinstance(ua_obj, dict) else None
        )

        if rid:
            try:
                rid_uuid = rid if isinstance(rid, UUID) else UUID(str(rid))
                role_ids.append(rid_uuid)
            except Exception:
                log.error(f"user_has_permission: Invalid role_id value: {rid}")

    log.info(f"user_has_permission: Extracted role_ids={role_ids}")
    if not role_ids:
        log.info("user_has_permission: No roles extracted from assignments")
        return False

    role_permissions = await FRTURolePermissions.select(role_id=role_ids)
    if not role_permissions:
        log.info("user_has_permission: No role_permissions found")
        return False

    perm_ids = []
    for rp in role_permissions:
        pid = None
        if isinstance(rp, dict) and "FRTURolePermissions" in rp:
            pid = getattr(rp["FRTURolePermissions"], "permission_id", None)
        elif hasattr(rp, "permission_id"):
            pid = getattr(rp, "permission_id", None)
        elif hasattr(rp, "_mapping"):
            pid = rp._mapping.get("permission_id")

        if pid:
            try:
                perm_ids.append(pid if isinstance(pid, UUID) else UUID(str(pid)))
            except Exception:
                log.error(f"user_has_permission: Invalid permission_id: {pid}")

    log.info(f"user_has_permission: Extracted permission_ids={perm_ids}")
    if not perm_ids:
        log.info("user_has_permission: No permission ids found for roles")
        return False

    permissions = await FRTUPermissions.select(id=perm_ids)
    if not permissions:
        log.info("user_has_permission: No permission records found")
        return False

    for perm in permissions:
        attr = None
        if isinstance(perm, dict) and "FRTUPermissions" in perm:
            attr = getattr(perm["FRTUPermissions"], "attribute", None)
        elif hasattr(perm, "attribute"):
            attr = getattr(perm, "attribute", None)
        elif hasattr(perm, "_mapping"):
            attr = perm._mapping.get("attribute")

        if not attr:
            continue

        resources = attr.get("resources") if isinstance(attr, dict) else None
        if not resources:
            continue

        for res in resources:
            r_name = (res.get("resource") or "").strip().upper()
            actions = [a.lower() for a in res.get("action", [])]
            if r_name == resource.strip().upper() and action.lower() in actions:
                log.info(f"user_has_permission: Permission matched for resource={resource}, action={action}")
                return True

    log.info("user_has_permission: No matching permission found")
    return False

