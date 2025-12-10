from typing import Literal
from uuid import UUID
from pydantic import BaseModel, field_validator

from src.enums.FrtuDeviceType import FrtuDeviceType

class AutoDiscoverEntity(BaseModel):
    name: str
    type: FrtuDeviceType

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()
    
class AutoDiscoverRequest(BaseModel):
    operation: Literal["create"]
    target:   Literal["asset"]
    entity:   AutoDiscoverEntity  # forward ref

AutoDiscoverRequest.model_rebuild()


class AutoDiscoverBySitePayload(BaseModel):
    site_id: UUID
    name:    str
    type:    FrtuDeviceType

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()
    