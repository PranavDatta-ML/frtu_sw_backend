import ipaddress
from typing import List, Literal, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field, validator
from enum import Enum


class Endianness(str, Enum):
    LITTLE_ENDIAN = "LITTLE_ENDIAN"
    BIG_ENDIAN = "BIG_ENDIAN"

class DataType(str, Enum):
    DT_32_BIT_FLOAT = "DT_32_BIT_FLOAT"
    DT_16_BIT_INT = "DT_16_BIT_INT"
    DT_32_BIT_INT = "DT_32_BIT_INT"

class ModbusFunctionCode(str, Enum):
    FC_1 = "1"
    FC_2 = "2"
    FC_3 = "3"
    FC_4 = "4"

class SlaveStatus(str, Enum):
    DISABLED = "0"
    ENABLED = "1"

class ParameterStatus(str, Enum):
    DISABLED = "0"
    ENABLED = "1"

# RTU models (your exact models)
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
    pollInterval: Optional[str] = None
    sid: Optional[str] = None
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

# TCP models (your exact models)
class TCPParameterConfig(BaseModel):
    parameterName: str
    description: Optional[str]
    address: str = Field(..., pattern=r"^\d{1,5}$")
    readFunctionCode: ModbusFunctionCode
    dataType: DataType
    endianness: Endianness
    ioa: str

class TCPParameter(BaseModel):
    id: Optional[str] = None
    status: ParameterStatus
    parameterConfig: TCPParameterConfig

class TCPSlaveConfig(BaseModel):
    name: str
    description: Optional[str]
    ipAddress: str
    port: str = Field(..., pattern=r"^\d{1,5}$")
    unitId: str = Field(..., pattern=r"^\d{1,3}$")
    accessToken: str = Field(..., min_length=4, max_length=100)
    maxParameters: str = Field(..., pattern=r"^\d{1,3}$")
    modbusParameters: List[TCPParameter]

    @validator("ipAddress")
    def validate_ip_address(cls, v):
        try:
            ipaddress.IPv4Address(v)
            return v
        except Exception:
            raise HTTPException(
                status_code=400,
                detail={"http_code": "400", "msg": "Invalid IP address format. Use IPv4 like 192.168.1.10"}
            )

class TCPSlave(BaseModel):
    id: Optional[str] = None
    status: SlaveStatus
    slaveConfig: TCPSlaveConfig

# Unified models
ProtocolType = Literal["Modbus RTU", "Modbus TCP"]

class UnifiedSlotInfo(BaseModel):
    slotId: str  # str works for both (convert UUID for RTU views)
    slotNumber: Optional[str] = None
    cardType: str
    slotDescription: Optional[str] = None

class UnifiedCategoryInfo(BaseModel):
    moduleId: str
    moduleName: str
    categoryDescription: Optional[str] = None
    communicationProtocol: ProtocolType
    hardwareVersion: str
    firmwareVersion: str
    
    # RTU-only fields
    maxChannels: Optional[str] = None
    channels: Optional[List[ModbusChannel]] = None
    
    # TCP-only fields
    maxSlaves: Optional[str] = None
    modbusSlaves: Optional[List[TCPSlave]] = None

    @validator('channels', 'modbusSlaves')
    def validate_protocol_fields(cls, v, values):
        if 'communicationProtocol' in values:
            protocol = values['communicationProtocol'].upper()
            has_channels = v is not None
            has_slaves = values.get('modbusSlaves') is not None
            
            if protocol == "MODBUS RTU":
                if not has_channels:
                    raise ValueError("RTU requires 'channels'")
                if has_slaves:
                    raise ValueError("RTU must not include 'modbusSlaves'")
            elif protocol == "MODBUS TCP":
                if not has_slaves:
                    raise ValueError("TCP requires 'modbusSlaves'")
                if has_channels:
                    raise ValueError("TCP must not include 'channels'")
        return v

class UnifiedModbusPayload(BaseModel):
    moduleId: str
    moduleType: str
    slotInfo: UnifiedSlotInfo
    categoryInfo: UnifiedCategoryInfo