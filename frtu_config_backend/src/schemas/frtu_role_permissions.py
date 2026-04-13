from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import UTC, datetime

class FRTURolePermissionBase(BaseModel):
    role_id: UUID
    permission_id: UUID

class AssignRolePermission(FRTURolePermissionBase):
    role_id: UUID = Field(..., description="Role ID")
    permission_id: UUID = Field(..., description="Permission ID")

class UpdateRolePermission(BaseModel):
    new_permission_id: UUID = Field(..., description="New Permission ID to update to")

class FRTURolePermissionRead(FRTURolePermissionBase):
    assigned_by: UUID
    role_id: UUID
    permission_id: UUID    
    role_created_by: Optional[UUID] = None
    permission_created_by: Optional[UUID] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        from_attributes = True
