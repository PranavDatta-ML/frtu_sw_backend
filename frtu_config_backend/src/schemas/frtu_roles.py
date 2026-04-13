from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from typing import List, Optional
from datetime import datetime, UTC

class FRTURoleBase(BaseModel):
    name: str = Field(..., description="Role name is required")
    description: Optional[str] = None
    attribute: Optional[dict] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

class FRTURoleCreate(FRTURoleBase):
    user_id: Optional[UUID] = None
    @field_validator("creation_time")
    def set_creation_time(cls, v):
        return datetime.now(UTC)

    @field_validator("last_update_time")
    def set_last_update_time(cls, v):
        return datetime.now(UTC)


class FRTURoleRead(FRTURoleBase):
    id: UUID
    user_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class PermissionItem(BaseModel):
    resource: str
    action: list[str]


class FRTURoleAdd(BaseModel):
    name: str
    permissions: list[PermissionItem]

class FRTURoleReadEntity(BaseModel):
    name: Optional[str] = None 

class FRTURoleReadPayload(BaseModel):
    entity: Optional[FRTURoleReadEntity] = None
    page: int = 1
    page_size: int = 10

class FRTURoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[PermissionItem]] = None

class FRTURoleOutPermission(BaseModel):
    resource: str
    action: str


class FRTURoleOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[FRTURoleOutPermission]