from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import UTC, datetime

class FRTUTenantBase(BaseModel):
    admin_id: UUID = Field(..., description="The tenant id field is required.")
    name: str = Field(..., description="The name field is required.")
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

class FRTUTenantCreate(FRTUTenantBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)

class FRTUTenantRead(FRTUTenantBase):
    id: int
    admin_id: int
    creation_time: datetime
    last_update_time: datetime

    class Config:
        from_attributes = True  
