from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.jwt_tokens import decode_access_token
from src.utils.permission_utils import user_has_permission

security = HTTPBearer()

# async def require_read_permission(
#     creds: HTTPAuthorizationCredentials = Depends(security),
# ):
#     token = creds.credentials
#     payload = decode_access_token(token)
#     user_id = payload.get("sub")
#     if not user_id:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

#     has_perm = await user_has_permission(user_id, "view")
#     if not has_perm:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Permission to read is required"
#         )
#     return user_id

async def require_read_permission(
    authorization: str = Header(...),
    resource: str = "ROLES"   # default, can be overridden per route
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header"
        )

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    has_perm = await user_has_permission(user_id, "view", resource)

    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No VIEW permission for resource '{resource}'"
        )

    return user_id



