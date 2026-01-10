from uuid import UUID
from pydantic import BaseModel
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
    id: Optional[UUID] = None
    status: str
    parameterConfig: ModbusParameterConfig

class ModbusSlaveConfig(BaseModel):
    name: str
    description: Optional[str]
    sid: str
    slaveName: Optional[str]
    accessToken: Optional[str]
    maxParameters: str
    modbusParameters: List[ModbusParameter]

class ModbusSlave(BaseModel):
    id: Optional[UUID] = None
    status: str
    slaveConfig: ModbusSlaveConfig

class ModbusChannelConfig(BaseModel):
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
    id: Optional[UUID] = None
    status: str
    channelConfig: ModbusChannelConfig

class SlotInfo(BaseModel):
    slotId: UUID
    slotNumber: Optional[str]
    cardType: str
    slotDescription: Optional[str]

class ModbusCategoryInfo(BaseModel):
    slotId: UUID   
    slotNumber: Optional[str]
    moduleId: str
    moduleName: str
    categoryDescription: Optional[str]
    communicationProtocol: ProtocolType
    hardwareVersion: str
    firmwareVersion: str
    maxChannels: str
    channels: List[ModbusChannel]

class ModbusPayload(BaseModel):
    slotInfo: SlotInfo
    categoryInfo: ModbusCategoryInfo
