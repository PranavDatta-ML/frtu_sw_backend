from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FRTUUserBase(BaseModel):
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    name: str
    attribute: Optional[dict] = None

class FRTUUserCreate(FRTUUserBase):
    password: str

class FRTUUserRead(FRTUUserBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class FRTUUserLogin(BaseModel):
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    password: str
