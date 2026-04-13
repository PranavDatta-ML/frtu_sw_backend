from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


class FRTUUserAssignmentBase(BaseModel):
    role_id: UUID
    user_id: UUID
    admin_id: UUID
    scope_id: Optional[UUID] = None
    scope_type: Optional[str]
    attribute: Optional[Any] = None
    
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

class FRTUUserAssignmentCreate(FRTUUserAssignmentBase):
    @field_validator("creation_time")
    def set_creation_time(cls, v):
        return datetime.now(UTC)

    @field_validator("last_update_time")
    def set_last_update_time(cls, v):
        return datetime.now(UTC)

class FRTUUserAssignmentUpdate(BaseModel):
    role_id: Optional[UUID] = None
    admin_id: Optional[UUID] = None
    scope_type: Optional[str] = None
    scope_id: Optional[UUID] = None
    attribute: Optional[Dict] = None

class FRTUUserAssignmentRead(FRTUUserAssignmentBase):
    id: UUID

    class Config:
        from_attributes = True
    

