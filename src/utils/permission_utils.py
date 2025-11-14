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

# =======================================================================Updated 14.11.2025=========================
# src/utils/permission_utils.py
from typing import List, Optional, Union
from uuid import UUID
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_roles import FRTURoles
from src import log


async def _extract_attr(row, key):
    try:
        if isinstance(row, dict):
            return row.get(key)
        return getattr(row, key)
    except Exception:
        return None


# async def user_has_permission(user_id: Union[str, UUID],action: str,resource: str,) -> bool:
#     log.info(f"user_has_permission: Checking user_id={user_id}, action={action}, resource={resource}")

#     user_assignments = await FRTUUserAssignment.select(user_id=user_id)
#     log.info(f"user_has_permission: user_assignments raw -> {user_assignments}")

#     role_ids: List[UUID] = []
#     for row in user_assignments or []:
#         if isinstance(row, dict):
#             r = row.get("role_id") or row.get("role")
#             if r:
#                 role_ids.append(r)
#                 continue
#         if hasattr(row, "role_id"):
#             role_ids.append(getattr(row, "role_id"))
#             continue
#         if isinstance(row, dict) and len(row) == 1:
#             val = next(iter(row.values()))
#             if hasattr(val, "role_id"):
#                 role_ids.append(getattr(val, "role_id"))

#     if not role_ids:
#         log.info("user_has_permission: No roles extracted from assignments")
#         return False

#     log.info(f"user_has_permission: Extracted role_ids={role_ids}")

#     role_permissions = await FRTURolePermissions.select(role_id=role_ids)
#     perm_ids = []
#     for rp in role_permissions or []:
#         if isinstance(rp, dict):
#             pid = rp.get("permission_id")
#             if pid:
#                 perm_ids.append(pid)
#                 continue
#         if hasattr(rp, "permission_id"):
#             perm_ids.append(getattr(rp, "permission_id"))
#             continue
#         if isinstance(rp, dict) and len(rp) == 1:
#             val = next(iter(rp.values()))
#             if hasattr(val, "permission_id"):
#                 perm_ids.append(getattr(val, "permission_id"))

#     if not perm_ids:
#         log.info("user_has_permission: No permission_ids found for roles")
#         return False

#     log.info(f"user_has_permission: Extracted permission_ids={perm_ids}")

#     permission_rows = await FRTUPermissions.select(id=perm_ids)
#     for prow in permission_rows or []:
#         attr = None
#         if isinstance(prow, dict):
#             attr = prow.get("attribute")
#         elif hasattr(prow, "attribute"):
#             attr = getattr(prow, "attribute")
#         if not attr:
#             continue
#         resources = attr.get("resources") if isinstance(attr, dict) and "resources" in attr else attr
#         if not resources:
#             continue
#         for res in resources:
#             res_name = res.get("resource") if isinstance(res, dict) else None
#             actions = res.get("action") if isinstance(res, dict) else None
#             if not res_name or not actions:
#                 continue
#             if str(res_name).upper() == str(resource).upper() and action.lower() in [a.lower() for a in actions]:
#                 log.info(f"user_has_permission: Permission matched for resource={resource}, action={action}")
#                 return True

#     log.info("user_has_permission: No matching permission found")
#     return False


