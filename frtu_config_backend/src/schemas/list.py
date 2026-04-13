from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import ClassVar
from typing import Optional

from src.core import Settings
    

class ListQueryParamSchema(BaseModel):
    """
    Schema for representing request details including time range, an external identifier, 
    and the protocol to be used for specific tasks.

    Attributes:
        from_time (datetime): The starting timestamp of the request.
        to_time (datetime): The ending timestamp of the request.
        external_id (Optional[UUID]): A unique identifier for the schedule (optional).
        protocol (Optional[str]): The protocol to be used for the task, such as HTTP (optional).
        ALLOWED_PROTOCOLS (ClassVar[set[str]]): A set of protocols allowed for validation.
    """

    from_time: datetime = Field(..., description="The starting timestamp of the request.")
    to_time: datetime = Field(..., description="The ending timestamp of the request.")
    external_id: Optional[UUID] = Field(None, description="An optional unique identifier for the schedule.")
    protocol: Optional[str] = Field(None, description="An optional protocol to be used for the task, such as HTTP.")

    ALLOWED_PROTOCOLS: ClassVar[set[str]] = set(Settings.get_settings().ALLOWED_HOOK_PROTOCOLS.split(','))

    @field_validator("protocol")
    def validate_protocol(cls, value: Optional[str]) -> Optional[str]:
        if value and value not in cls.ALLOWED_PROTOCOLS:
            allowed_protocols = ', '.join(cls.ALLOWED_PROTOCOLS)
            raise ValueError(f"Invalid protocol '{value}'. Allowed protocols are: {allowed_protocols}")
        return value