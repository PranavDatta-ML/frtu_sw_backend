from fastapi import HTTPException
import jwt # type: ignore
from src.config.auth_config import ALGORITHM, SECRET_KEY


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")




# from datetime import datetime, timedelta
# import jwt
# import secrets

# SECRET_KEY = secrets.token_hex(32)
# # SECRET_KEY = "YOUR_SECRET_KEY"  # replace with secure key
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60

# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# def decode_token(token: str):
#     try:
#         return jwt.decode(
#             token,
#             SECRET_KEY,
#             algorithms=ALGORITHM,
#             options={"verify_exp": True}
#         )
#     except jwt.ExpiredSignatureError:
#         return None
#     except jwt.InvalidTokenError:
#         return None

