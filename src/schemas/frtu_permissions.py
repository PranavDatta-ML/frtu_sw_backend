from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import UTC, datetime

class FRTUPermissionBase(BaseModel):
    # name: str = Field(..., description="Permission name is required")
    # description: Optional[str] = None
    attribute: Optional[Any] = None

# class FRTUPermissionCreate(FRTUPermissionBase):
#     @field_validator("creation_time")
#     def set_creation_time(cls, v):
#         return datetime.now(UTC)

#     @field_validator("last_update_time")
#     def set_last_update_time(cls, v):
#         return datetime.now(UTC)

class FRTUPermissionCreate(FRTUPermissionBase):
    attribute: List[Dict[str, Any]] = Field(..., description="List of resource-action mappings")
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    @field_validator("creation_time", mode="before")
    def set_creation_time(cls, v):
        return v or datetime.now(UTC)

    @field_validator("last_update_time", mode="before")
    def set_last_update_time(cls, v):
        return v or datetime.now(UTC)


class FRTUPermissionUpdate(FRTUPermissionBase):
    attribute: Optional[Any] = None

class FRTUPermissionRead(FRTUPermissionBase):
    id: UUID
    user_id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        from_attributes = True



