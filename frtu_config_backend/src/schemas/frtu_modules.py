
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional
from datetime import UTC, datetime

class FRTUModuleBase(BaseModel):
    slot_id: UUID
    name: str
    module_type: str
    description: Optional[str] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

class AddModuleAutoRequest(BaseModel):
    module_id: UUID
    module_type: str

class AddModuleManuallyRequest(BaseModel):
    module_id: UUID
    module_type: str      # e.g. "DO"
    slot_id: UUID

class DeviceModuleItem(BaseModel):
    slot_id: UUID
    module_id: UUID
    module_type: str      # PS / SOM / COM / DI / DO / AI ...
    module_name: str

class DeviceModulesResponse(BaseModel):
    status: str
    device_id: UUID
    device_type: str
    is_auto: Optional[bool] = None
    modules: List[Dict[str, Any]]

class GroupedDIModule(BaseModel):
    module_name: str
    module_type: str
    id: UUID | None
    di_modules: List[DeviceModuleItem]


class GroupedDOModule(BaseModel):
    module_name: str
    module_type: str
    id: UUID | None
    do_modules: List[DeviceModuleItem]

# class DeviceModulesResponse(BaseModel):
#     status: str
#     device_id: UUID
#     device_type: str
#     is_auto: Optional[bool] = None
#     Modules: List[Dict[str, Any]]

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

class DeviceModuleCreate(BaseModel):
    site_id: UUID          
    slot_no: int           
    module_id: UUID       
    config: Dict[str, Any] = {}