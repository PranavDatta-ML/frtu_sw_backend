from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel


class BaseConfigPayload(BaseModel):
    config_json: Dict[str, Any]
    attribute: Optional[Dict[str, Any]] = {}

class BaseConfigResponse(BaseModel):
    device_id: UUID
    config_json: Dict[str, Any]
    attribute: Dict[str, Any]
    last_synced_at: Optional[str]