from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import UTC, datetime

class FRTUProjectBase(BaseModel):
    # tenant_id: UUID = Field(..., description="The tenant id field is required.")
    name: str = Field(..., description="The name field is required.")
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

class FRTUProjectCreate(FRTUProjectBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)
    
class FRTUProjectUpdate(BaseModel):
    name: str  # Required to find the project by name
    status: Optional[str] = None
    orderDate: Optional[str] = None
    last_update_time: Optional[datetime] = None

    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

# class FRTUProjectUpdate(BaseModel):
#     name: Optional[str] = None
#     description: Optional[str] = None

class FRTUProjectRead(FRTUProjectBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


