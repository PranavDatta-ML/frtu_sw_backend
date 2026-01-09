from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class ModbusSlotInfo(BaseModel):
    slotNumber: UUID
    cardType: Literal["Modbus (Com.3)"]
    description: str

class ModbusCategoryInfo(BaseModel):
    moduleId: UUID
    moduleName: str
    slotDescription: str
    communicationProtocol: Literal["Modbus (Com.3)"]
    maxChannels: str
    maxSlaves: str

class ModbusBase(BaseModel):
    slave_id: UUID