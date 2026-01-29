from src.services.redis_service import confirm_password_reset, request_password_reset, send_otp, verify_otp
from src.core.status_codes import HttpStatusCode
from src.models.frtu_roles import FRTURoles
from src.models.frtu_user_assignment import FRTUUserAssignment
from src.models.frtu_users import FRTUUsers
from src.schemas.auth import OTPSendRequest, OTPVerifyRequest, ResetConfirmBody, ResetRequestBody
from src.utils.jwt_tokens import create_access_token, create_refresh_token


async def send_otp_login(request: OTPSendRequest):
    return await send_otp(request.email)

# async def verify_otp_login(request: OTPVerifyRequest):
#     stored_otp, is_valid = await verify_otp(request.email, request.otp)
    
#     if not is_valid:
#         return stored_otp  # Error response
    
#     users = await FRTUUsers.select(email=request.email)
#     if not users:
#         return HttpStatusCode.NOT_FOUND.response("User not found")
    
#     user = users[0]
#     user_assignment = await FRTUUserAssignment.select(user_id=user.id)
#     role_id = None
#     role_name = None
    
#     if user_assignment:
#         role_id = str(user_assignment[0].role_id)
#         role_rec = await FRTURoles.select(id=user_assignment[0].role_id)
#         if role_rec:
#             role_name = role_rec[0].name

#     token = create_access_token(
#         sub=str(user.id),
#         extra_claims={
#             "name": user.name,
#             "email": user.email,
#             "role_id": role_id,
#             "role": role_name
#         }
#     )
    
#     refresh_token = create_refresh_token(
#         sub=str(user.id),
#         extra_claims={
#             "name": user.name,
#             "email": user.email,
#             "role_id": role_id,
#             "role": role_name
#         }
#     )
    
#     return {
#         "http_code": 200,
#         "code": "OK",
#         "message": "Login successful",
#         "data": {
#             "access_token": token,
#             "refresh_token": refresh_token
#         },
#         "user_id": str(user.id),
#         "role_id": role_id,
#         "role_name": role_name,
#         "name": user.name,
#         "email": user.email
#     }

async def verify_otp_login(request: OTPVerifyRequest):
    error_response, is_valid = await verify_otp(request.email, request.otp)

    if not is_valid:
        return error_response  # Stop login here

    users = await FRTUUsers.select(email=request.email)
    if not users:
        return HttpStatusCode.NOT_FOUND.response("User not found")

    user = users[0]
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

    return {
        "http_code": 200,
        "code": "OK",
        "message": "Login successful",
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


async def send_reset_request(request: ResetRequestBody):
    return await request_password_reset(request.email)

async def verify_reset_request(request: ResetConfirmBody):
    return await confirm_password_reset(request.token, request.password)
