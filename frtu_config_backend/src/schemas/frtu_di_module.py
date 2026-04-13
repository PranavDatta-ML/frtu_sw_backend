from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from uuid import UUID

class ConfigureDIModule(BaseModel):
    module_id: UUID        
    module_type: str       
    slot_id: Optional[UUID] = None
    general_info: Dict[str, Any] = {}

class ConfigureDIModuleRequest(BaseModel):
    sub_module_id: UUID        
    module_type: str       
    slot_id: Optional[UUID] = None
    general_info: Dict[str, Any] = {}   

class AddDIChannelPayload(BaseModel):
    sub_module_id: UUID          # frtu_modules.id
    channel_no: int

class DIChannelInfo(BaseModel):
    channel_id: str 
    name: Optional[str] = None 
    description: Optional[str] = None

    ioa: Optional[str] = None
    io_activation_mode: Optional[str] = None
    timestamp_enable: Optional[bool] = None
    normal_state: Optional[str] = None
    inverse: Optional[bool] = None
    debounce_filter_ms: Optional[str] = None
    high_level_filter_ms: Optional[str] = None
    low_level_filter_ms: Optional[str] = None
    is_enabled: Optional[Union[bool, int]] = None
    tag_name: Optional[str] = None
    equipment_id: Optional[str] = None
    equipment_type: Optional[str] = None
    equipment_name: Optional[str] = None
    scada_point_type: Optional[str] = None
    grouping: Optional[str] = None
    alarm_category: Optional[str] = None
    event_classification: Optional[str] = None
    command_configuration_source: Optional[str] = None

    channel_type: Optional[str] = None                     # "Single Point Parameter" | "Double Point Parameter"
    # associate_channel_no: Optional[str] = None  # e.g. "DI Channel 1"
    associate_channel_id: Optional[str] = None
    dp_group_id: Optional[str] = None  # "DP1", "DP2", ..., "DP8"
    release_dp_group: Optional[bool] = False

class ConfigureSingleDIChannelRequest(BaseModel):
    sub_module_id: UUID
    channel: DIChannelInfo

class GetDIChannelRequest(BaseModel):
    sub_module_id: UUID

class ConfigureModuleIOARequest(BaseModel):
    sub_module_id: UUID
    base_ioa: Optional[int] = None  
    channels: Optional[List[Dict[str, str]]] = None  

class ConfigureModuleIOAResponse(BaseModel):
    status: str
    message: str
    device_id: str
    sub_module_id: str
    ioa_mapping: List[Dict[str, str]]

class ConfigureMultipleDIChannelsRequest(BaseModel):
    sub_module_id: UUID
    channels: List[DIChannelInfo]
    
# class ConfigureDIChannelsRequest(BaseModel):
#     module_id: UUID          # frtu_modules.id (DI module instance)
#     module_type: str         # "DI"
#     channels: List[DIChannelConfig]
