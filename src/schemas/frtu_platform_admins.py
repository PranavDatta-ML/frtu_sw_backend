
from typing import Dict, Optional, Any
from uuid import UUID
from datetime import datetime, UTC
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator
from src.utils.security import generate_salt, hash_password

class FRTUPlatformAdminBase(BaseModel):
    name: str = Field(..., description="Name field is required")
    # password: str = Field(..., description="Password field is required")
    mobile_no: str
    email: Optional[EmailStr] = None
    attribute: Optional[dict] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

class FRTUPlatformAdminCreate(FRTUPlatformAdminBase):
    # removed created_by field
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)


class FRTUPlatformAdminUpdate(BaseModel):
    name: Optional[str] = None
    # password_hash: Optional[str] = None
    # salt: Optional[str] = None
    mobile_no: Optional[str] = None
    attribute: Optional[dict[str, Any]] = None


class FRTUPlatformAdminOut(BaseModel):
    id: UUID
    name: str
    email: str
    mobile_no: str
    attribute: Optional[Dict]
    created_by: Optional[UUID]
    creation_time: datetime
    last_update_time: datetime
    # roles: Optional[list] = None       # NEW
    # permissions: Optional[list] = None # NEW

    class Config:
        orm_mode = True

