from uuid import UUID
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

ProtocolType = Literal["Modbus RTU", "Modbus TCP"]

class ModbusParameterConfig(BaseModel):
    parameterName: str
    description: Optional[str]
    address: str
    readFunctionCode: str
    dataType: str
    endianness: str
    ioa: str

class ModbusParameter(BaseModel):
    id: Optional[str] = Field(None)
    status: str
    parameterConfig: ModbusParameterConfig

class ModbusSlaveConfig(BaseModel):
    name: str
    description: Optional[str]
    pollInterval: Optional[str] = None  # RTU
    sid: Optional[str] = None           # RTU
    slaveName: Optional[str]
    pollInterval: Optional[str]
    accessToken: Optional[str]
    maxParameters: str
    modbusParameters: List[ModbusParameter]

class ModbusSlave(BaseModel):
    id: Optional[str] = Field(None)
    status: str
    slaveConfig: ModbusSlaveConfig

class ModbusChannelConfig(BaseModel):
    channelNo: str
    channelName: str
    description: Optional[str]
    serialPort: str
    baudRate: str
    parity: str
    dataBits: str
    stopBits: str
    maxSlaves: str
    modbusSlaves: List[ModbusSlave]

class ModbusChannel(BaseModel):
    id: Optional[str] = Field(None)
    status: str
    channelConfig: ModbusChannelConfig

class SlotInfo(BaseModel):
    slotId: UUID
    slotNumber: Optional[str]
    cardType: str
    slotDescription: Optional[str]

class ModbusCategoryInfo(BaseModel):
    # slotId: Optional[UUID]   
    # slotNumber: Optional[str]
    moduleId: str
    moduleName: str
    categoryDescription: Optional[str]
    communicationProtocol: ProtocolType
    hardwareVersion: str
    firmwareVersion: str
    maxChannels: Optional[str] = None
    channels: Optional[List[ModbusChannel]] = None       # RTU
    modbusSlaves: Optional[List[ModbusSlave]] = None

class ModbusPayload(BaseModel):
    moduleId: str
    moduleType: str
    slotInfo: SlotInfo
    categoryInfo: ModbusCategoryInfo
