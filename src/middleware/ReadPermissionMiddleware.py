from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.jwt_tokens import decode_access_token
from src.utils.permission_utils import user_has_permission

security = HTTPBearer()

async def require_read_permission(
    creds: HTTPAuthorizationCredentials = Depends(security),
):
    token = creds.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    has_perm = await user_has_permission(user_id, "read_permission")
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission to read is required"
        )
    return user_id
