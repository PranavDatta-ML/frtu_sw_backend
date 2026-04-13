from fastapi import APIRouter, Body, Request, Depends

from src import Settings
from src.schemas.auth import OTPSendRequest, OTPVerifyRequest, ResetConfirmBody, ResetRequestBody
from src.views.auth import validate
from src.views.email_otp import send_otp_login, send_reset_request, verify_otp_login, verify_reset_request

router = APIRouter(
    prefix="/auth",
    tags=['auth']
)


@router.post("/login")
async def login_post(request: Request, settings: Settings = Depends(Settings.get_settings)):
    return await validate(request, settings)

@router.post("/login/otp", response_model=dict)
async def api_send_otp_login(request: OTPSendRequest):
    return await send_otp_login(request)

@router.post("/verify/otp", response_model=dict)
async def api_verify_otp_login(request: OTPVerifyRequest):
    return await verify_otp_login(request)

@router.post("/reset-password/request")
async def api_reset_password_request(request: ResetRequestBody):
    return await send_reset_request(request)

@router.post("/reset-password/confirm")
async def api_reset_password_confirm(request: ResetConfirmBody):
    return await verify_reset_request(request)