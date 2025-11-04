from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import UTC, datetime

class FRTURolePermissionBase(BaseModel):
    role_id: UUID
    permission_id: UUID

class FRTURolePermissionCreate(FRTURolePermissionBase):
    @field_validator("creation_time")
    def set_creation_time(cls, v):
        return datetime.now(UTC)

    @field_validator("last_update_time")
    def set_last_update_time(cls, v):
        return datetime.now(UTC)

class FRTURolePermissionRead(FRTURolePermissionBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        from_attributes = True
