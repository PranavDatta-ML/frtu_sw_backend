from fastapi import Request

from src.schemas.auth import AuthBase
from src.models.frtu_users import FRTUUser
from src.utils.schema import verify_schema
from src.utils.security import hash_password
from src import Settings, HttpStatusCode
from src.utils.jwt_tokens import create_access_token


async def validate(request: Request, settings: Settings):
    ok, messages, data = await verify_schema(await request.json(), AuthBase)

    if not ok:
        return HttpStatusCode.BAD_REQUEST.response(message=messages)

    try:
        condition = {"email": data.username, "mobile_no": data.username}
        users = await FRTUUser.select(use_or=True, **condition)

        if not users:
            return HttpStatusCode.NOT_FOUND.response(message="User not found!")

        user: FRTUUser = users[0]

        hashed_password = hash_password(data.password, user.salt)
        if hashed_password != user.password_hash:
            return HttpStatusCode.BAD_REQUEST.response(message="Invalid password")

        token = create_access_token(
            sub=str(user.id),
            extra_claims={
                "name": user.name,
                "role": "admin"
            }
        )
        return HttpStatusCode.OK.response(message="Login successfully done", data=token)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


