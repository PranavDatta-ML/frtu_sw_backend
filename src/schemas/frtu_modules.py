# schemas/frtu_modules.py
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import UTC, datetime

class FRTUModuleBase(BaseModel):
    slot_id: UUID
    name: str
    module_type: str
    description: Optional[str] = None

class FRTUModuleCreate(FRTUModuleBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)

class FRTUModuleRead(FRTUModuleBase):
    id: UUID
    creation_time: Optional[datetime]
    last_update_time: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True

class ModuleSummary(BaseModel):
    Power_Supply: Optional[str]
    Communication_Module: Optional[str]
    SOM_Module: Optional[str]
    DI_Modules: Optional[str]
    DO_Modules: Optional[str]

class AutoDiscoverResponse(BaseModel):
    frtuName: str
    frtuType: str
    totalSlots: int
    emptySlots: int
    totalDI: int
    totalDO: int
    modules: ModuleSummary