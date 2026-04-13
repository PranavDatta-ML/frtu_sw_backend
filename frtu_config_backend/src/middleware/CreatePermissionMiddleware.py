
import logging
from uuid import UUID
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.jwt_tokens import decode_access_token
from src.utils.permission_utils import user_has_permission

security = HTTPBearer()


async def require_create_permission(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    user_sub = payload.get("sub")
    if not user_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_uuid = UUID(str(user_sub))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id in token")

    has_perm = await user_has_permission(user_uuid, "edit", "PERMISSION")
    if not has_perm:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission to create is required")
    return user_uuid

def require_permission(action: str, resource: str):
    async def wrapper(authorization: str = Header(...)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header"
            )

        token = authorization.split(" ")[1]
        payload = decode_access_token(token)

        user_sub = payload.get("sub")
        if not user_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        try:
            user_uuid = UUID(user_sub)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID in token"
            )

        allowed = await user_has_permission(user_uuid, action, resource)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have '{action}' permission for '{resource}'"
            )

        return user_uuid

    return wrapper