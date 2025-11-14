
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

#=============================================================================14.11.2025
# src/middleware/CreatePermissionMiddleware.py
from uuid import UUID
from fastapi import Header, HTTPException, status
from src.utils.jwt_tokens import decode_access_token
from src.utils.permission_utils import user_has_permission
from src import log

# async def require_create_permission(authorization: str = Header(...)):
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
#     token = authorization.split(" ")[1]
#     payload = decode_access_token(token)
#     user_sub = payload.get("sub")
#     if not user_sub:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
#     try:
#         user_uuid = UUID(str(user_sub))
#     except Exception:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id in token")

#     # Check create/edit permission for PERMISSION (roles+permissions creation) or ROLE as needed.
#     # We check "edit" permission for resource PERMISSION to allow creation as per your earlier flow.
#     has_perm = await user_has_permission(user_uuid, "edit", "PERMISSION")
#     if not has_perm:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission to create is required")
#     return user_uuid
