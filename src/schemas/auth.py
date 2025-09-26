from pydantic import BaseModel, Field


class AuthBase(BaseModel):
    username: str = Field(..., description="Name field is required")
    password: str = Field(..., description="Password field is required")
