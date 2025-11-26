from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Dict, Optional
from datetime import UTC, datetime

class FRTUProjectBase(BaseModel):
    # tenant_id: UUID = Field(..., description="The tenant id field is required.")
    name: str = Field(..., description="The name field is required.")
    type: Optional[str] = "project"
    attribute: Optional[dict] = None
    # description: Optional[str] = None
    
    last_update_time: Optional[datetime] = None
    creation_time: Optional[datetime] = None


class FRTUProjectCreate(BaseModel):
    operation: str = Field(..., example="create")
    target: str = Field(..., example="project")

    class Entity(BaseModel):
        tenant_id: UUID
        name: str
        type: Optional[str] = "project"
        label: Optional[str] = None
        description: Optional[str] = None
        communicationType: Optional[dict] = None
        Maximum_RTUs: Optional[str] = None
        status: Optional[str] = None
        orderDate: Optional[str] = None
        orderNumber: Optional[str] = None

    entity: Entity



class FRTUProjectDelete(BaseModel):
    operation: str
    target: str
    entity: Dict[str, Any]

    @model_validator(mode="after")
    def validate_name(self):
        if "name" not in self.entity or not self.entity["name"]:
            raise ValueError("Project name is required to delete a project")
        return self

class FRTUProjectDeleteByID(BaseModel):
    operation: str
    target: str
    entity: Dict[str, Any]

    @model_validator(mode="after")
    def validate_id(self):
        if "id" not in self.entity or not self.entity["id"]:
            raise ValueError("Project ID is required to delete project")
        return self

    
class FRTUProjectUpdateByName(BaseModel):
    operation: str
    target: str
    entity: Dict[str, Any]

    @model_validator(mode="after")
    def validate_name(self):
        if "name" not in self.entity or not self.entity["name"]:
            raise ValueError("Project name is required for update-by-name")
        return self


class FRTUProjectUpdateById(BaseModel):
    operation: str
    target: str
    entity: Dict[str, Any]

class FRTUProjectRead(BaseModel):
    operation: str
    target: str


