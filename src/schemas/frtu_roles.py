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
    @field_validator("creation_time")
    def set_creation_time(cls, v):
        return datetime.now(UTC)

    @field_validator("last_update_time")
    def set_last_update_time(cls, v):
        return datetime.now(UTC)

class FRTURoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = None

class FRTURoleRead(FRTURoleBase):
    id: UUID
    user_id: UUID

    class Config:
        from_attributes = True
