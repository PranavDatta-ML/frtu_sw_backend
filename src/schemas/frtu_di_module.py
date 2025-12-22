from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID

class ConfigureDIModuleRequest(BaseModel):
    module_id: UUID        
    module_type: str       
    slot_id: Optional[UUID] = None
    general_info: Dict[str, Any] = {}   
