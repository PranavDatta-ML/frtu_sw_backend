from pydantic import BaseModel, EmailStr, Field


class AuthBase(BaseModel):
    username: str = Field(..., description="Name field is required")
    password: str = Field(..., description="Password field is required")

class OTPSendRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetRequestBody(BaseModel):
    email: EmailStr

class ResetConfirmBody(BaseModel):
    token: str
    password: str