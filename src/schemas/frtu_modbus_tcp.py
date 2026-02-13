from enum import Enum
import ipaddress
from uuid import UUID
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

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
    slaveName: Optional[str]
    description: Optional[str]
    ipAddress: str 
    port: str = Field(..., pattern=r"^\d{1,5}$")
    unitId: str = Field(..., pattern=r"^\d{1,3}$")
    accessToken: str = Field(..., min_length=4, max_length=100)
    maxParameters: str = Field(..., pattern=r"^\d{1,3}$")
    modbusParameters: List[TCPParameter]
    @field_validator("ipAddress")
    @classmethod
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

class TCPModbusCategoryInfo(BaseModel):
    moduleId: str
    moduleName: str
    categoryDescription: Optional[str]
    communicationProtocol: str
    hardwareVersion: str
    firmwareVersion: str
    maxSlaves: str
    modbusSlaves: List[TCPSlave]

class SlotInfo(BaseModel):
    slotId: str
    slotNumber: Optional[str]
    cardType: str
    slotDescription: Optional[str]

class ModbusTCPPayload(BaseModel):
    moduleId: str
    moduleType: str
    slotInfo: SlotInfo
    categoryInfo: TCPModbusCategoryInfo

class TCPParameterResponse(BaseModel):
    id: str
    status: str
    parameterConfig: TCPParameterConfig

class TCPSlaveConfigResponse(BaseModel):
    name: str
    description: Optional[str]
    ipAddress: str
    port: str
    unitId: str
    accessToken: str
    maxParameters: str
    modbusParameters: List[TCPParameterResponse]

class TCPSlaveResponse(BaseModel):
    id: str
    status: str
    slaveConfig: TCPSlaveConfigResponse

class TCPModbusCategoryInfoResponse(BaseModel):
    moduleId: str
    moduleName: str
    categoryDescription: Optional[str]
    communicationProtocol: str
    hardwareVersion: str
    firmwareVersion: str
    maxSlaves: str
    modbusSlaves: List[TCPSlaveResponse]

class ModbusTCPResponse(BaseModel):
    status: str
    moduleId: str
    moduleType: str
    deviceId: str
    slotInfo: SlotInfo
    categoryInfo: TCPModbusCategoryInfoResponse
   