from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import UTC, datetime

class FRTUEntityBase(BaseModel):
    name: str = Field(..., description="Entity name (Platform Admin, Tenant, etc.)")
    email_id: EmailStr = Field(..., description="Email ID of the entity")
    mobile_no: Optional[str] = Field(None, description="Mobile number of the entity")
    attribute: Optional[Any] = Field({}, description="Additional attributes as JSON")


class FRTUEntityCreate(FRTUEntityBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)


class FRTUEntityRead(FRTUEntityBase):
    id: UUID
    entity_id: Optional[UUID]
    created_by: Optional[UUID]
    creation_time: datetime
    last_update_time: datetime

    class Config:
        orm_mode = True
        from_attributes = True