from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    attribute: Optional[Dict] = None

class RoleRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]

class PermissionCreate(BaseModel):
    attribute: List[Dict]

class RolePermissionAssign(BaseModel):
    role_id: UUID
    permission_id: UUID

class UserRoleAssign(BaseModel):
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_id: Optional[UUID]