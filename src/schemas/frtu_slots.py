from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import UTC, datetime

class FRTUSlotBase(BaseModel):
    device_id: UUID = Field(..., description="The device id field is required.")
    name: str = Field(..., description="The name field is required.")
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

class FRTUSlotCreate(FRTUSlotBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)
    
class FRTUSlotUpdate(BaseModel):
    name: str  
    status: Optional[str] = None
    orderDate: Optional[str] = None
    last_update_time: Optional[datetime] = None

    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

# class FRTUProjectUpdate(BaseModel):
#     name: Optional[str] = None
#     description: Optional[str] = None

class FRTUSlotRead(FRTUSlotBase):
    id: UUID
    device_id: UUID
    name: str
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


