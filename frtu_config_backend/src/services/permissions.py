from collections import defaultdict
from uuid import UUID

from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_user_assignment import FRTUUserAssignment
async def _get_permissions_grouped(role_ids: list[UUID]) -> dict[UUID, dict[str, set[str]]]:
    if not role_ids:
        return {}

    role_perms = await FRTURolePermissions.select(role_id=role_ids)
    perm_ids = [rp.permission_id for rp in role_perms]
    if not perm_ids:
        return {}

    perms = await FRTUPermissions.select(id=perm_ids)
    perms_by_id = {p.id: (p.attribute or {}) for p in perms}

    grouped: dict[UUID, dict[str, set[str]]] = {}

    for rp in role_perms:
        attr = perms_by_id.get(rp.permission_id) or {}

        resources_list = attr.get("resources")
        if isinstance(resources_list, list):
            for item in resources_list:
                res = item.get("resource")
                actions = item.get("action")
                if not res or not actions:
                    continue
                role_map = grouped.setdefault(rp.role_id, defaultdict(set))
                for act in actions:
                    role_map[res].add(act)
            continue

        res = attr.get("resource")
        act = attr.get("action")
        if res and act:
            role_map = grouped.setdefault(rp.role_id, defaultdict(set))
            role_map[res].add(act)

    return grouped

async def _user_can_view_all_roles(user_id: UUID) -> bool:
    # find all role_ids for user
    assignments = await FRTUUserAssignment.select(user_id=user_id)
    role_ids = [a.role_id for a in assignments]
    if not role_ids:
        return False

    # find permissions for these roles
    grouped = await _get_permissions_grouped(role_ids)

    for rid, res_map in grouped.items():
        actions = res_map.get("ROLES")  # resource name for role management
        if actions and ("edit" in actions or "view_all" in actions):
            return True
    return False


async def user_can_assign_roles(user_id: UUID) -> bool:
    # find all roles assigned to this user
    assignments = await FRTUUserAssignment.select(user_id=user_id)
    role_ids = [a.role_id for a in assignments]
    if not role_ids:
        return False

    # role -> permission_id
    rps = await FRTURolePermissions.select(role_id=role_ids)
    perm_ids = [rp.permission_id for rp in rps]
    if not perm_ids:
        return False

    perms = await FRTUPermissions.select(id=perm_ids)
    for p in perms:
        attr = p.attribute or {}
        resources_list = attr.get("resources") or []
        for item in resources_list:
            res = item.get("resource")
            actions = item.get("action") or []
            # decide what "can assign roles" means; here ROLES or USERS with create/edit
            if res in ("ROLES", "USERS") and any(a in ("create", "edit") for a in actions):
                return True
    return False