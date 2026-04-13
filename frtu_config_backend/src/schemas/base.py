from pydantic import BaseModel, Field, field_validator
from typing import ClassVar
from typing import List
from datetime import datetime
from uuid import UUID

from src.core import Settings

    
class LogSchema(BaseModel):
    """
    Schema for the task logging configuration.
    """
    enabled: bool = Field(..., description="Flag to enable or disable logging for the task.")
    duration: int = Field(..., description="Duration (in seconds) for which logs should be retained. If set to -1, logs will be retained indefinitely.")

    @field_validator("duration")
    def validate_duration(cls, value: int):
        if value < -1:
            raise ValueError("Duration must be -1 (infinite) or a non-negative integer.")
        return value
    

class BaseSchema(BaseModel):
    """
    Schema for scheduling tasks with associated request, configuration, and notification details.
    """
    timestamp: datetime = Field(..., description="Timestamp indicating when the schedule was created.")
    external_id: UUID = Field(..., description="Unique identifier for the schedule.")
    protocol: str = Field(..., description="Protocol to be used for the task, such as HTTP.")
    timeout: int = Field(..., description="Timeout duration for the request, in seconds.")
    start_ts: datetime = Field(..., description="The start time for the task.")
    interval: List[int] = Field(..., description="List of intervals (in seconds) at which the task should run.")
    log: LogSchema = Field(..., description="Logging configuration for the task.")

    ALLOWED_PROTOCOLS: ClassVar[set[str]] = set(Settings.get_settings().ALLOWED_HOOK_PROTOCOLS.split(','))

    @field_validator("protocol")
    def validate_protocol(cls, value: str):
        if value not in cls.ALLOWED_PROTOCOLS:
            raise ValueError(f"Invalid protocol '{value}'. Allowed protocols are: {', '.join(cls.ALLOWED_PROTOCOLS)}")
        return value
    
    @field_validator("interval")
    def check_non_negative(cls, values: List[int]):
        if any([ value < 0 for value in values ]):
            raise ValueError("All values in `intervals` must be non-negative integers.")
        return values