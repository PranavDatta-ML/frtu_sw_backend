import time
from typing import Dict

from fastapi import HTTPException, Header
import jwt
import uuid
from src.core.settings import Settings
from src.core.status_codes import HttpStatusCode
from fastapi import Depends, HTTPException, Header, Request, status

JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
def create_access_token(sub: str, extra_claims: dict | None = None) -> str:
    settings = Settings()
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        # "exp": now + settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        "exp": now + (JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        "jti": str(uuid.uuid4()),
        **(extra_claims or {}),
    }
    if settings.JWT_AUDIENCE:
        payload["aud"] = settings.JWT_AUDIENCE
    if settings.JWT_ISSUER:
        payload["iss"] = settings.JWT_ISSUER
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str):
    settings = Settings()
    try:
        return jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM],  # Should be a list
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,  # Skip audience verification
                "verify_iss": False   # Skip issuer verification
            }
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")


async def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: user_id missing")
    try:
        # Validate UUID format
        uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id in token")
    return user_id

async def get_current_user(authorization: str = Header(...)) -> Dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    
    token = authorization.split(" ")[1]
    
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        return {
            "user_id": user_id,
            "name": payload.get("name"),
            "email": payload.get("email"),
            "role": payload.get("role")
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
JWT_REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

def create_refresh_token(sub: str, extra_claims: dict | None = None) -> str:
    settings = Settings()
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + (JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
        **(extra_claims or {}),
    }
    if settings.JWT_AUDIENCE:
        payload["aud"] = settings.JWT_AUDIENCE
    if settings.JWT_ISSUER:
        payload["iss"] = settings.JWT_ISSUER
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)