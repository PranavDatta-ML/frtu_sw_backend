from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, root_validator


class ConfigureModuleManuallyRequest(BaseModel):
    module_id: UUID
    module_type: str
    slot_info: Optional[Dict[str, Any]] = None
    category_info: Optional[Dict[str, Any]] = None


class GetConfiguredModuleResponse(BaseModel):
    status: str
    http_code: int
    message: str
    module_id: UUID
    module_type: str
    device_id: UUID
    slot_info: Optional[Dict[str, Any]] = None
    category_info: Optional[Dict[str, Any]] = None