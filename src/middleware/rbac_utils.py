


import uuid
from src.core.status_codes import HttpStatusCode
from src.models.frtu_permissions import FRTUPermissions
from src.models.frtu_role_permissions import FRTURolePermissions
from src.utils.jwt_tokens import decode_access_token


async def verify_user_permission(authorization: str, resource: str, action: str):
    if not authorization or not authorization.startswith("Bearer "):
        return HttpStatusCode.UNAUTHORIZED.response(message="Invalid Authorization header")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    role_id = payload.get("role_id")

    if not role_id:
        return HttpStatusCode.UNAUTHORIZED.response(message="User has no role assigned")

    permissions = await FRTURolePermissions.select(role_id=uuid.UUID(role_id))
    if not permissions:
        return HttpStatusCode.FORBIDDEN.response(message="User has no permissions assigned")

    allowed = False

    for perm in permissions:
        perm_data = await FRTUPermissions.select(id=perm["permission_id"])
        if not perm_data:
            continue
        perm_attr = perm_data[0].get("attribute", {})
        for res in perm_attr.get("resources", []):
            if res["resource"].upper() == resource.upper() and action.lower() in [a.lower() for a in res["action"]]:
                allowed = True
                break
        if allowed:
            break

    if not allowed:
        return HttpStatusCode.FORBIDDEN.response(
            message=f"You do not have '{action}' access to resource '{resource}'"
        )

    return None
