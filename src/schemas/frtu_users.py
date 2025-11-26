from uuid import UUID
from pydantic import BaseModel, Field, EmailStr
from typing import Dict
from typing import Optional
from datetime import datetime

class FRTUUserBase(BaseModel):
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    name: str
    attribute: Optional[dict] = None

class FRTUUserCreate(FRTUUserBase):
    password: str

class FRTUUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_no: Optional[str] = None
    attribute: Optional[Dict] = None


class FRTUUserRead(BaseModel):
    id: UUID
    name: str
    email: str
    mobile_no: str
    is_active: bool
    is_deleted: bool
    attribute: dict
    creation_time: datetime
    last_update_time: datetime
    created_by: Optional[UUID] = None

    class Config:
        orm_mode = True

class FRTUUserLogin(BaseModel):
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    password: str
