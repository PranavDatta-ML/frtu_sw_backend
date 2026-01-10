from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
import enum

class ChannelType(str, enum.Enum):
    SINGLE_POINT_PARAMETER = "Single Point Parameter"
    DOUBLE_POINT_PARAMETER = "Double Point Parameter"

class ChannelInfo(BaseModel):
    channelNoPrimary: str
    name: str
    description: str
    ioa: str
    status: bool
    ioActivationMode: str
    timestampEnable: bool
    normalState: str
    inverse: bool
    debounceFilter: str
    highLevelFilter: str
    lowLevelFilter: str
    tagName: Optional[str] = None
    equipmentId: Optional[str] = None
    equipmentType: Optional[str] = None
    equipmentName: Optional[str] = None
    scadaPointType: Optional[str] = None
    grouping: Optional[str] = None
    alarmCategory: Optional[str] = None
    eventClassification: Optional[str] = None
    commandConfigurationSource: Optional[str] = None
    channelType: ChannelType
    associateChannelNo: Optional[str] = None

class ConfigureDIModuleRequest(BaseModel):
    module_id: UUID
    module_type: str
    slot_id: UUID
    general_info: Optional[Dict[str, Any]] = None
    channels: Optional[List[ChannelInfo]] = Field(default_factory=list)

class ConfigureDIChannelResponse(BaseModel):
    status: str = "success"
    message: str
    device_id: str
    sub_module_id: str
    channels_count: int
    associateable_channels: list = Field(default_factory=list)

class GetDIModuleInfoResponse(BaseModel):
    status: str = "success"
    http_code: int = 200
    message: str
    data: Dict[str, Any]

class GetDIModuleRequest(BaseModel):
    module_id: UUID  # frtu_module_master.id
    module_type: str
    slot_id: UUID
    device_id: str 

class GetDIModuleData(BaseModel):
    module_id: str
    slot_id: str
    module_type: str
    name: Optional[str] = None
    general_info: Optional[Dict[str, Any]] = None
    channels: Optional[List[ChannelInfo]] = Field(default_factory=list)
    configured_channels_count: int = 0

class DIGeneralInfo(BaseModel):
    card_type: str
    name: str
    description: str | None
    serial_number: str
    type: str
    hardware_version: str
    firmware_version: str
class DIModulePayload(BaseModel):
    module_id: UUID
    module_type: str
    slot_id: UUID
    general_info: DIGeneralInfo
    channels: list[ChannelInfo] | None = None

