import time
import jwt
import uuid
from src.core.settings import Settings

def create_access_token(sub: str, extra_claims: dict | None = None) -> str:
    settings = Settings()
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        "jti": str(uuid.uuid4()),
        **(extra_claims or {}),
    }
    if settings.JWT_AUDIENCE:
        payload["aud"] = settings.JWT_AUDIENCE
    if settings.JWT_ISSUER:
        payload["iss"] = settings.JWT_ISSUER
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)