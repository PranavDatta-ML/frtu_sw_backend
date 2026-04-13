from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional
from datetime import UTC, datetime

class FRTUTenantBase(BaseModel):
    admin_id: UUID = Field(..., description="The tenant id field is required.")
    name: str = Field(..., description="The name field is required.")
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

# class FRTUTenantCreate(FRTUTenantBase):
#     name: str = Field(..., description="The name field is required.")
#     attribute: Optional[dict] = None
#     @field_validator("last_update_time")
#     def set_last_update_time(cls, value: datetime):
#         return datetime.now(UTC)

#     @field_validator("creation_time")
#     def set_creation_time(cls, value: datetime):
#         return datetime.now(UTC)
    
class FRTUTenantCreate(BaseModel):
    name: str = Field(..., description="The name field is required.")
    # admin_id: UUID 
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    attribute: Optional[Dict] = None
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

class FRTUTenantUpdate(BaseModel):
    name: Optional[str] = None
    attribute: Optional[Dict] = None


class FRTUTenantRead(BaseModel):
    id: UUID
    name: str
    admin_id: UUID
    attribute: Optional[Dict]
    created_by: Optional[UUID]
    creation_time: datetime
    last_update_time: datetime
    class Config:
        from_attributes = True  

class FRTUTenantOut(BaseModel):
    id: UUID
    created_by: UUID
    # role_id: UUID
    admin_id: UUID
    name: str
    attribute: Optional[Dict[str, Any]]

    class Config:
        orm_mode = True