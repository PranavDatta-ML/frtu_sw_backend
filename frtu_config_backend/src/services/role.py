from math import ceil
from uuid import UUID
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.models.frtu_user_assignment import FRTUUserAssignment


async def _get_role_permissions_map(role_ids: list[UUID]) -> dict[UUID, list[dict]]:
    if not role_ids:
        return {}

    rps = await FRTURolePermissions.select(role_id=role_ids)
    perm_ids = [rp.permission_id for rp in rps]
    if not perm_ids:
        return {}

    perms = await FRTUPermissions.select(id=perm_ids)
    perms_by_id = {p.id: (p.attribute or {}) for p in perms}

    grouped: dict[UUID, list[dict]] = {}
    for rp in rps:
        attr = perms_by_id.get(rp.permission_id) or {}
        resources = attr.get("resources") or []
        # normalize to [{resource, actions}]
        for item in resources:
            res = item.get("resource")
            acts = item.get("action") or []
            if not res or not acts:
                continue
            grouped.setdefault(rp.role_id, []).append(
                {"resource": res, "actions": acts}
            )
    return grouped


async def _get_role_permissions(role_id: UUID) -> list[dict]:
    rps = await FRTURolePermissions.select(role_id=role_id)
    if not rps:
        return []

    perm_ids = [rp.permission_id for rp in rps]
    perms = await FRTUPermissions.select(id=perm_ids)
    perms_by_id = {p.id: (p.attribute or {}) for p in perms}

    out: list[dict] = []
    for rp in rps:
        attr = perms_by_id.get(rp.permission_id) or {}
        resources = attr.get("resources") or []
        for item in resources:
            res = item.get("resource")
            acts = item.get("action") or []
            if not res or not acts:
                continue
            out.append({"resource": res, "actions": acts})
    return out

async def _user_has_role(user_id: UUID, role_id: UUID) -> bool:
    assignments = await FRTUUserAssignment.select(user_id=user_id, role_id=role_id)
    return bool(assignments)