from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime, UTC
from pydantic import BaseModel, Field, field_validator

from src.enums.FrtuDeviceType import FrtuDeviceType


class FRTUDeviceBase(BaseModel):
    name: str
    type: FrtuDeviceType
    attribute: Optional[Dict] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

class FRTUDeviceCreateEntity(BaseModel):
    name: str
    type: str
    label: Optional[str] = None
    description: Optional[str] = None
    parentName: Optional[str] = None
    site_id: Optional[UUID] = None
    module: Optional[str] = None
    no_of_Slave_Rack: Optional[str] = None

    class Config:
        extra = "allow"

class FRTUDeviceCreate(BaseModel):
    operation: str
    target: str
    entity: FRTUDeviceCreateEntity

class FRTUDeviceCreate(BaseModel):
    operation: str
    target: str
    entity: FRTUDeviceCreateEntity

class FRTUDeviceReadEntity(BaseModel):
    device_id: Optional[UUID] = None
    name: Optional[str] = None

class FRTUDeviceRead(BaseModel):
    operation: str
    target: str
    entity: Optional[FRTUDeviceReadEntity] = None


class FRTUDeviceUpdateEntity(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None

    class Config:
        extra = "allow"

class FRTUDeviceUpdate(BaseModel):
    operation: str
    target: str
    entity: FRTUDeviceUpdateEntity

class FRTUDeviceDeleteEntity(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None

class FRTUDeviceDelete(BaseModel):
    operation: str
    target: str
    entity: FRTUDeviceDeleteEntity

class FRTUDeviceOut(BaseModel):
    id: UUID
    site_id: UUID
    name: str
    type: str
    attribute: Optional[Dict]
    creation_time: Optional[datetime]
    last_update_time: Optional[datetime]

    class Config:
        orm_mode = True

