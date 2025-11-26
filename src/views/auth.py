from fastapi import Request

from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.schemas.auth import AuthBase
from src.models.frtu_users import FRTUUsers
from src.utils.schema import verify_schema
from src.utils.security import hash_password
from src import Settings, HttpStatusCode
from src.utils.jwt_tokens import create_access_token, create_refresh_token


async def validate(request: Request, settings: Settings):
    ok, messages, data = await verify_schema(await request.json(), AuthBase)

    if not ok:
        return HttpStatusCode.BAD_REQUEST.response(message=messages)

    try:
        condition = {"email": data.username, "mobile_no": data.username}
        users = await FRTUUsers.select(use_or=True, **condition)

        if not users:
            return HttpStatusCode.NOT_FOUND.response(message="User not found!")

        user: FRTUUsers = users[0]

        hashed_password = hash_password(data.password, user.salt)
        if hashed_password != user.password_hash:
            return HttpStatusCode.BAD_REQUEST.response(message="Invalid password")
        
        # user_assignment = await FRTUUserAssignment.select(user_id=user["id"])
        # role_id = None
        # if user_assignment:
        #     role_id = str(user_assignment[0]["role_id"])

        # user_assignment = await FRTUUserAssignment.select(user_id=user.id)
        # role_id = None
        # if user_assignment:
        #     role_id = str(user_assignment[0].role_id)


        # token = create_access_token(
        #     sub=str(user.id),
        #     extra_claims={
        #         "name": user.name,
        #         "role": "admin"
        #     }
        # )

        # refresh_token = create_refresh_token(
        #     sub=str(user.id),
        #     extra_claims={
        #         "name": user.name,
        #         "email": user.email,
        #         "role_id": role_id
        #     }
        # )
        
        user_assignment = await FRTUUserAssignment.select(user_id=user.id)
        role_id = None
        role_name = None

        if user_assignment:
            role_id = str(user_assignment[0].role_id)
            role_rec = await FRTURoles.select(id=user_assignment[0].role_id)
            if role_rec:
                role_name = role_rec[0].name

        token = create_access_token(
            sub=str(user.id),
            extra_claims={
                "name": user.name,
                "email": user.email,
                "role_id": role_id,
                "role": role_name
            }
        )

        refresh_token = create_refresh_token(
            sub=str(user.id),
            extra_claims={
                "name": user.name,
                "email": user.email,
                "role_id": role_id,
                "role": role_name
            }
        )

        resp = {
            "http_code": 200,
            "code": "OK",
            "message": "Login successful",
            # "token": token,
            # "refresh_token": refresh_token,
            "data": {
                "access_token": token,
                "refresh_token": refresh_token
            },
            "user_id": str(user.id),
            "role_id": role_id,
            "role_name": role_name,
            "name": user.name,
            "email": user.email
        }
        return resp
        # return HttpStatusCode.OK.response(message="Login successfully done", data=token)
    except Exception as e:
        return HttpStatusCode.BAD_REQUEST.response(message=str(e))


