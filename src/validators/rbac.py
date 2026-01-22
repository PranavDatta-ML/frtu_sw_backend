from uuid import UUID
from fastapi import Depends, HTTPException, Header

from src.services.rbac import RBACService
from src.utils.jwt_tokens import decode_access_token

async def current_user(authorization: str = Header(...)) -> UUID:
    token = authorization.split(" ")[1]
    decoded = decode_access_token(token)
    return UUID(decoded["sub"])

def require_permission(action: str, resource: str):
    async def guard(user_id: UUID = Depends(current_user)):
        rbac = RBACService(user_id)
        if not await rbac.has_permission(action, resource):
            raise HTTPException(403, "Permission denied")
        return user_id
    return guard