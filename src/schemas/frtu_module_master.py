
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import UTC, datetime

class FRTUModuleMasterBase(BaseModel):
    name: str
    attribute: Optional[dict] = None

class FRTUModuleMasterCreate(FRTUModuleMasterBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)

class FRTUModuleMasterRead(FRTUModuleMasterBase):
    id: UUID
    creation_time: Optional[datetime]
    last_update_time: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True
