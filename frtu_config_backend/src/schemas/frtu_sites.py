from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional
from datetime import UTC, datetime


class FRTUSiteCreate(BaseModel):
    operation: str = "create"
    target: str = "site"

    entity: Dict = Field(
        ..., 
        description="Site data including name, device_type, description & other attributes"
    )

    class Config:
        extra = "allow"

class FRTUSiteRead(BaseModel):
    operation: str
    target: str
    entity: Optional[Dict] = None

class FRTUSiteOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    attribute: Optional[str]
    creation_time: Optional[datetime]
    last_update_time: Optional[datetime]
    class Config:
        orm_mode = True



class FRTUSiteBase(BaseModel):
    # project_id: UUID = Field(..., description="The project id field is required.")
    name: str = Field(..., description="The name field is required.")
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None

    
class FRTUSiteUpdateEntity(BaseModel):
    id: Optional[UUID] = None        
    name: Optional[str] = None        
    label: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    status: Optional[str] = None
    device_type: Optional[str] = None 

    class Config:
        extra = "allow"     


class FRTUSiteUpdate(BaseModel):
    operation: str
    target: str
    entity: FRTUSiteUpdateEntity

    class Config:
        extra = "forbid"


class FRTUSiteReadEntity(BaseModel):
    name: Optional[str] = None
    id: Optional[UUID] = None   # for get-by-id

class FRTUSiteReadPayload(BaseModel):
    operation: str
    target: str
    entity: Optional[FRTUSiteReadEntity] = None

class FRTUSimpleReadPayload(BaseModel):
    operation: str
    target: str


