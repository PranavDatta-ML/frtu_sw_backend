from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ModuleMasterItem(BaseModel):
    id: UUID
    name: str
    attribute: Optional[dict] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class ModuleMasterListResponse(BaseModel):
    status: str = Field("success")
    code: str = Field("MODULE_MASTER_LIST")
    message: str = Field("Module master list fetched successfully.")
    modules: List[str]