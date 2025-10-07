from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import UTC, datetime

class FRTUSiteBase(BaseModel):
    # project_id: UUID = Field(..., description="The project id field is required.")
    name: str = Field(..., description="The name field is required.")
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

class FRTUSiteCreate(FRTUSiteBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)
    
class FRTUSiteUpdate(BaseModel):
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

class FRTUSiteRead(FRTUSiteBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


