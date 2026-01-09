import enum
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

IOActivationMode = Literal["0", "1", "2"]
PulseType = Literal["0", "1", "2"]
SBOFlag = Literal["0", "1"]
NormalState = Literal["ON", "OFF"]

# class ChannelType(str, enum.Enum):
#     SINGLE_POINT_PARAMETER = "Single Point Parameter"
#     DOUBLE_POINT_PARAMETER = "Double Point Parameter"

class DOChannel(BaseModel):
    channelNoPrimary: str
    name: str
    description: Optional[str] = None
    ioa: str
    ioActivationMode: IOActivationMode
    status: bool
    timestampEnable: bool
    PulseType: PulseType
    sboFlag: SBOFlag
    channelType: Literal[
        "Single Point Parameter",
        "Double Point Parameter"
    ]
    associateChannelNo: Optional[str] = None
    normalState: NormalState
    inverse: Optional[bool] = False
    shortPulse: Optional[str] = False
    longPulse: Optional[str] = False

    tagName: Optional[str] = None
    equipmentId: Optional[str] = None
    equipmentType: Optional[str] = None
    equipmentName: Optional[str] = None
    scadaPointType: Optional[str] = None
    grouping: Optional[str] = None
    alarmCategory: Optional[str] = None
    commandConfigurationSource: Optional[str] = None


class DOModulePayload(BaseModel):
    module_id: UUID
    module_type: Literal["DO"]
    slot_id: UUID
    general_info: Optional[dict] = None
    channels: Optional[List[DOChannel]] = None