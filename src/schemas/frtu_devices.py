from typing import Optional
from uuid import UUID
from datetime import datetime, UTC
from pydantic import BaseModel, Field, field_validator

from src.enums.FrtuDeviceType import FrtuDeviceType

class FRTUDeviceBase(BaseModel):
    site_id: UUID = Field(..., description="The site id field is required.")
    name: str = Field(..., description="The name field is required.")
    type: FrtuDeviceType
    attribute: Optional[dict] = None

    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

class FRTUDeviceCreate(FRTUDeviceBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)


# Schema for update (partial fields)
class FRTUDeviceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    attribute: Optional[dict] = None
    last_update_time: Optional[datetime] = None

    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)


# Schema for reading from DB (including ID and timestamps)
class FRTUDeviceRead(FRTUDeviceBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True
